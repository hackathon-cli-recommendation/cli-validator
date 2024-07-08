import asyncio
from asyncio import Task
from collections import defaultdict
from typing import List, Any, Optional

from cli_validator.exceptions import CommandMetaNotFoundException
from cli_validator.repo.base import RepoMetaRetrieverBase, RepoBase
from cli_validator.repo.utils import retrieve_command_tree, retrieve_latest_version, retrieve_meta
from cli_validator.cmd_tree import CommandSource, CommandTreeParser


class ExtensionMetaRetriever(RepoMetaRetrieverBase):
    EXTENSION_COMMAND_TREE_URL = \
        'https://azurecliextensionsync.blob.core.windows.net/cmd-index/extensionCommandTree.json'
    EXTENSION_DIR = 'azure-cli-extensions'

    def __init__(self, shared_cache: Optional[defaultdict[Any, dict]] = None):
        self._source = CommandSource.EXTENSION
        # Could not use `shared_cache or defaultdict(lambda: {})` since shared_cache could be empty dict
        if shared_cache is not None:
            self._shared_cache = shared_cache
        else:
            self._shared_cache = defaultdict(lambda: {})
        self._command_tree: Optional[Task[CommandTreeParser]] = None
        # Please note the leaf node is asyncio.Task.
        self._private_cache = {}

    @property
    def source(self) -> CommandSource:
        return self._source

    async def command_tree(self) -> CommandTreeParser:
        if not self._command_tree:
            self._command_tree = asyncio.create_task(self._retrieve_command_tree())
        return await self._command_tree

    async def _retrieve_command_tree(self) -> CommandTreeParser:
        return await retrieve_command_tree(self.EXTENSION_COMMAND_TREE_URL, self.source)

    async def _get_extension_meta(self, ext: str):
        version_file = await self.retrieve_last_version(ext)
        if version_file not in self._shared_cache[ext]:
            url = f'{self.BLOB_URL}/{self.CONTAINER_NAME}/{self.EXTENSION_DIR}/ext-{ext}/{version_file}'
            # Assume that in most cases, after updating shared cache with the latest version,
            # no other MetaLoader will require an older version.
            # Meanwhile, existing MetaLoader could still use the older one in private cache.
            # self._shared_cache[ext] = {version_file: asyncio.create_task(retrieve_meta(url))}
            # Need Lock to implement the upper logic
            self._shared_cache[ext][version_file] = asyncio.create_task(retrieve_meta(url))
        return await self._shared_cache[ext][version_file]

    async def get_extension_meta(self, ext: str):
        if ext not in self._private_cache:
            self._private_cache[ext] = asyncio.create_task(self._get_extension_meta(ext))
        return await self._private_cache[ext]

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


class ExtensionRepo(RepoBase):
    def __init__(self):
        self._source = CommandSource.EXTENSION
        # Please note the leaf node is asyncio.Task.
        self._meta_cache = defaultdict(lambda: {})

    @property
    def meta_retriever(self) -> ExtensionMetaRetriever:
        return ExtensionMetaRetriever(self._meta_cache)
