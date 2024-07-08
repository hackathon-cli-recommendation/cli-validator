import asyncio
import logging
import re
from typing import List, Optional

from .base import RepoMetaRetrieverBase, RepoBase
from .utils import retrieve_command_tree, retrieve_meta, retrieve_latest_version, retrieve_list
from cli_validator.exceptions import CommandMetaNotFoundException, MetadataException
from cli_validator.cmd_tree import CommandSource, CommandTreeParser


logger = logging.getLogger(__name__)


class CoreRepoMetaRetriever(RepoMetaRetrieverBase):
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
            self._command_tree = asyncio.create_task(self._retrieve_command_tree())
        return await self._command_tree

    async def _retrieve_command_tree(self) -> CommandTreeParser:
        url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.version_dir}/command_tree.json'
        return await retrieve_command_tree(url, self.source)

    async def get_module_meta(self, module: str) -> dict:
        if module not in self._metas:
            url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.version_dir}/az_{module}_meta.json'
            meta = asyncio.create_task(retrieve_meta(url))
            self._metas[module] = meta
        return await self._metas[module]

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


class LatestCoreRepoMetaRetriever(RepoMetaRetrieverBase):
    def __init__(self, shared_cache: Optional[dict] = None):
        self._versioned_retriever = None
        # Could not use `shared_cache or {}` since shared_cache could be empty dict
        if shared_cache is not None:
            self._shared_cache = shared_cache
        else:
            self._shared_cache = {}

    async def _get_latest_versioned_retriever(self):
        try:
            latest_version = await CoreRepoMetaRetriever.latest_version()
        except MetadataException as e:
            if self._shared_cache:
                logger.warning(f'Fail to retrieve metadata due to {e}. Using cached version.')
                return await list(self._shared_cache.values())[-1]
            raise e from e
        if latest_version not in self._shared_cache:
            self._shared_cache[latest_version] = CoreRepoMetaRetriever(latest_version)
        return self._shared_cache[latest_version]

    async def versioned_retriever(self) -> CoreRepoMetaRetriever:
        if not self._versioned_retriever:
            self._versioned_retriever = asyncio.create_task(self._get_latest_versioned_retriever())
        return await self._versioned_retriever

    async def command_tree(self) -> CommandTreeParser:
        retriever = await self.versioned_retriever()
        return await retriever.command_tree()

    @property
    def source(self) -> CommandSource:
        return CommandSource.CORE_MODULE

    async def load_command_meta(self, signature: List[str], module: str) -> dict:
        retriever = await self.versioned_retriever()
        return await retriever.load_command_meta(signature, module)


class CoreRepo(RepoBase):
    def __init__(self):
        self._shared_cache = {}

    @property
    def meta_retriever(self) -> LatestCoreRepoMetaRetriever:
        return LatestCoreRepoMetaRetriever(self._shared_cache)
