import asyncio
import logging
from typing import List, Optional, Any, Generator

from cli_validator.cmd_tree import CommandInfo
from cli_validator.exceptions import CommandTreeCorruptedException, UnknownCommandException, MissingSubCommandException
from cli_validator.repo import RepoMetaRetrieverBase, ExtensionMetaRetriever, LatestCoreRepoMetaRetriever, CoreRepo, \
    ExtensionRepo
from cli_validator.cmd_tree import CommandSource

logger = logging.getLogger(__name__)


class CommandMetadata(object):
    def __init__(self, command_info: CommandInfo, metadata: Optional[dict], source: CommandSource):
        self.module = command_info.module
        self.signature = command_info.signature
        self.parameters = command_info.parameters
        self.source = source
        self.metadata = metadata

    @property
    def is_help(self):
        return self.module is None


class MetaRetriever(object):
    def __init__(self, core_repo: LatestCoreRepoMetaRetriever, extension_repo: ExtensionMetaRetriever):
        self.core_repo = core_repo
        self.extension_repo = extension_repo

    def repos(self) -> Generator[RepoMetaRetrieverBase, Any, Any]:
        yield self.core_repo
        yield self.extension_repo

    @staticmethod
    async def _retrieve_meta(repo, command: List[str]):
        command_tree = await repo.command_tree()
        cmd_info = command_tree.parse_command(command)
        if cmd_info.module is None:
            return CommandMetadata(cmd_info, None, command_tree.source)
        meta = await repo.load_command_meta(cmd_info.signature, cmd_info.module)
        return CommandMetadata(cmd_info, meta, command_tree.source)

    async def retrieve_meta(self, command: List[str]):
        tasks = [self._retrieve_meta(repo, command) for repo in self.repos()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        metas = [result for result in results if isinstance(result, CommandMetadata)]
        corrupted_exc = [result for result in results if isinstance(result, CommandTreeCorruptedException)]
        missing_sub_exc = [result for result in results if isinstance(result, MissingSubCommandException)]
        unknown_cmd_exc = ([UnknownCommandException(' '.join(command))] +
                           [result for result in results if isinstance(result, UnknownCommandException)])
        other_exc = [result for result in results
                     if isinstance(result, Exception) and result not in missing_sub_exc + unknown_cmd_exc]

        for e in corrupted_exc + other_exc:
            logger.warning(e.msg, exc_info=e)
        if metas:
            return metas[0]
        if other_exc:
            raise other_exc[0]
        if missing_sub_exc:
            raise missing_sub_exc[0]
        raise unknown_cmd_exc[-1]


class MetaRetrieverFactory(object):
    def __init__(self):
        self.core_repo = CoreRepo()
        self.extension_repo = ExtensionRepo()

    @property
    def retriever(self) -> MetaRetriever:
        return MetaRetriever(self.core_repo.meta_retriever, self.extension_repo.meta_retriever)
