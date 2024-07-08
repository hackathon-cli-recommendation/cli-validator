from abc import abstractmethod, ABC
from typing import List

from cli_validator.cmd_tree import CommandSource, CommandTreeParser


class RepoMetaRetrieverBase(ABC):
    BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
    CONTAINER_NAME = 'cmd-metadata-per-version'

    async def command_tree(self) -> CommandTreeParser:
        raise NotImplementedError()

    @property
    @abstractmethod
    def source(self) -> CommandSource:
        raise NotImplementedError()

    @abstractmethod
    async def load_command_meta(self, signature: List[str], module: str) -> dict:
        raise NotImplementedError()


class RepoBase(ABC):
    @property
    @abstractmethod
    def meta_retriever(self) -> RepoMetaRetrieverBase:
        raise NotImplementedError()
