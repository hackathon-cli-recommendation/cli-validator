import logging
from typing import List, Optional, Any, Generator

from cli_validator.cmd_tree import CommandInfo
from cli_validator.exceptions import MetadataException, CommandTreeCorruptedException, UnknownCommandException, \
    MissingSubCommandException
from cli_validator.repo import RepoBase, CoreRepo, ExtensionRepo
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
    def __init__(self, core_repo: CoreRepo, extension_repo: ExtensionRepo):
        self.core_repo = core_repo
        self.extension_repo = extension_repo

    def repos(self) -> Generator[RepoBase, Any, Any]:
        yield self.core_repo
        yield self.extension_repo

    async def retrieve_meta(self, command: List[str]):
        missing_sub = []
        unknown_cmd = [UnknownCommandException(' '.join(command))]
        for repo in self.repos():
            try:
                command_tree = await repo.command_tree()
                cmd_info = command_tree.parse_command(command)
                if cmd_info.module is None:
                    return CommandMetadata(cmd_info, None, command_tree.source)
                meta = await repo.load_command_meta(cmd_info.signature, cmd_info.module)
                return CommandMetadata(cmd_info, meta, command_tree.source)
            except CommandTreeCorruptedException as e:
                logger.warning(e.msg, exc_info=e)
            except MissingSubCommandException as e:
                missing_sub.append(e)
            except UnknownCommandException as e:
                unknown_cmd.append(e)
        raise missing_sub[-1] if missing_sub else unknown_cmd[-1]


class MetaRetrieverFactory(object):
    def __init__(self):
        self._core_repo: Optional[CoreRepo] = None
        self._extension_repo = ExtensionRepo()

    async def new(self) -> MetaRetriever:
        return MetaRetriever(await self.core_repo(), self._extension_repo)

    async def core_repo(self):
        try:
            latest_version = await CoreRepo.latest_version()
            if not (self._core_repo and latest_version == self._core_repo.version_dir):
                self._core_repo = CoreRepo(latest_version)
        except MetadataException as e:
            if self._core_repo:
                logger.warning('Fail to Get Latest Version/Metadata of Core Repo. Using Cached Metadata.')
                return self._core_repo
            else:
                raise e
        return self._core_repo
