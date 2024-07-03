import asyncio
import re
from typing import List, Optional

from .base import RepoBase
from .utils import retrieve_command_tree, retrieve_meta, retrieve_latest_version, retrieve_list
from cli_validator.exceptions import CommandMetaNotFoundException
from cli_validator.cmd_tree import CommandSource, CommandTreeParser


class CoreRepo(RepoBase):
    def __init__(self, version):
        if re.match(r'\d+\.\d+\.\d+', version):
            version_dir = f'azure-cli-{version}'
        else:
            version_dir = version
        self._source = CommandSource.CORE_MODULE
        self.version_dir = version_dir
        self._command_tree: Optional[CommandTreeParser] = None
        self._metas = {}

    @classmethod
    async def latest_version(cls):
        url = f'{cls.BLOB_URL}/{cls.CONTAINER_NAME}/version_list.txt'
        return await retrieve_latest_version(url)

    @property
    def source(self) -> CommandSource:
        return self._source

    async def command_tree(self) -> CommandTreeParser:
        if not self._command_tree:
            self._command_tree = await self._retrieve_command_tree()
        return self._command_tree

    async def _retrieve_command_tree(self) -> CommandTreeParser:
        url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.version_dir}/command_tree.json'
        return await retrieve_command_tree(url, self.source)

    async def get_module_meta(self, module: str) -> dict:
        if module not in self._metas:
            url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.version_dir}/az_{module}_meta.json'
            meta = await retrieve_meta(url)
            self._metas[module] = meta
        return self._metas[module]

    async def get_full_metas(self) -> dict:
        modules_url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.version_dir}/index.txt'
        module_files = await retrieve_list(modules_url)
        modules = [file[3: -10] for file in module_files]
        tasks = [self.get_module_meta(module) for module in modules]
        return dict(zip(modules, list(await asyncio.gather(*tasks))))

    async def load_command_meta(self, signature: List[str], module: str) -> dict:
        meta = await self.get_module_meta(module)
        try:
            for idx in range(len(signature) - 1):
                meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
            return meta['commands'][' '.join(signature)]
        except KeyError as e:
            raise CommandMetaNotFoundException(signature) from e
