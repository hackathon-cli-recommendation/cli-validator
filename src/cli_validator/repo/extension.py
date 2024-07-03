from collections import defaultdict
from typing import List

from cli_validator.exceptions import CommandMetaNotFoundException
from cli_validator.repo.base import RepoBase
from cli_validator.repo.utils import retrieve_command_tree, retrieve_latest_version, retrieve_meta
from cli_validator.cmd_tree import CommandSource, CommandTreeParser


class ExtensionRepo(RepoBase):
    EXTENSION_COMMAND_TREE_URL = \
        'https://azurecliextensionsync.blob.core.windows.net/cmd-index/extensionCommandTree.json'
    EXTENSION_DIR = 'azure-cli-extensions'

    def __init__(self):
        self._source = CommandSource.EXTENSION
        self._meta_cache = defaultdict(lambda: {})

    @property
    def source(self) -> CommandSource:
        return self._source

    async def _retrieve_command_tree(self) -> CommandTreeParser:
        return await retrieve_command_tree(self.EXTENSION_COMMAND_TREE_URL, self.source)

    async def get_extension_meta(self, ext: str):
        version_file = await self.retrieve_last_version(ext)
        if version_file not in self._meta_cache[ext]:
            url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.EXTENSION_DIR}/ext-{ext}/{version_file}'
            self._meta_cache[ext][version_file] = await retrieve_meta(url)
        return self._meta_cache[ext][version_file]

    async def load_command_meta(self, signature: List[str], module: str) -> dict:
        meta = await self.get_extension_meta(module)
        try:
            for idx in range(len(signature) - 1):
                meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
            return meta['commands'][' '.join(signature)]
        except KeyError as e:
            raise CommandMetaNotFoundException(signature) from e

    async def retrieve_last_version(self, extension: str):
        url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.EXTENSION_DIR}/ext-{extension}/version_list.txt'
        return await retrieve_latest_version(url)
