from enum import Enum
from typing import Optional, List

from cli_validator.cmd_tree import CommandTreeParser


class CacheStrategy(str, Enum):
    CacheAside = 'CacheAside'
    Fallback = 'Fallback'


class BaseLoader(object):
    def __init__(self):
        self.metas = None
        self.command_tree: Optional[CommandTreeParser] = None

    def load_command_meta(self, signature: List[str], module: str):
        """
        Load metadata of specific command.
        :param signature: command signature
        :param module:
        :return:
        """
        if not self.metas:
            return None
        module_meta = self.metas[f'az_{module}_meta.json']
        meta = module_meta
        for idx in range(len(signature) - 1):
            meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
        return meta['commands'][' '.join(signature)]
