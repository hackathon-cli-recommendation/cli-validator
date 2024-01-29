from typing import Optional

from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.loader import BaseLoader
from cli_validator.loader.cmd_meta import load_metas
from cli_validator.result import CommandSource


class CoreRepoLoader(BaseLoader):
    BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
    CONTAINER_NAME = 'cmd-metadata-per-version'

    def __init__(self, cache_dir: Optional[str] = './core_repo'):
        """
        :param cache_dir: cache directory that store the downloaded metadata
        """
        super().__init__()
        self.cache_dir = cache_dir

    def load(self, version: Optional[str] = None, force_refresh=False):
        """
        :param version: the version of `azure-cli` that provides the metadata
        :param force_refresh: load the metadata through network no matter whether there is a cache
        """
        self.metas = load_metas(version, self.cache_dir, force_refresh=force_refresh)
        self.command_tree = build_command_tree(self.metas, CommandSource.CORE_MODULE)

    async def load_async(self, version: Optional[str] = None, force_refresh=False):
        from cli_validator.loader.cmd_meta.aio import load_metas
        self.metas = await load_metas(version, self.cache_dir, force_refresh=force_refresh)
        self.command_tree = build_command_tree(self.metas, CommandSource.CORE_MODULE)


def _attach_sub_group_to_node(sub_group, tree_node, module):
    for name, command in sub_group["commands"].items():
        tree_node[name.split()[-1]] = module
    for name, sub_group in sub_group["sub_groups"].items():
        name = name.split()[-1]
        if name not in tree_node:
            tree_node[name] = {}
        next_tree_node = tree_node[name]
        _attach_sub_group_to_node(sub_group, next_tree_node, module)


def build_command_tree(metas, source):
    tree = {}
    for meta in metas.values():
        module = meta["module_name"]
        _attach_sub_group_to_node(meta, tree, module)
    return CommandTreeParser(tree, source)
