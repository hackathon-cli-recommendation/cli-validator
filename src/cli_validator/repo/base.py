from abc import abstractmethod, ABC
from typing import List

from cli_validator.cmd_tree import CommandSource, CommandTreeParser


class RepoBase(ABC):
    BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
    CONTAINER_NAME = 'cmd-metadata-per-version'

    async def command_tree(self) -> CommandTreeParser:
        return await self._retrieve_command_tree()

    @property
    @abstractmethod
    def source(self) -> CommandSource:
        raise NotImplementedError()

    @abstractmethod
    async def _retrieve_command_tree(self) -> CommandTreeParser:
        raise NotImplementedError()

    @abstractmethod
    async def load_command_meta(self, signature: List[str], module: str) -> dict:
        raise NotImplementedError()
