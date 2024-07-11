import json
import logging
import os
from typing import Optional, List

import requests

from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.exceptions import CommandMetaNotFoundException, ExtensionNotFoundException
from cli_validator.loader import BaseLoader, CacheStrategy
from cli_validator.loader.cmd_meta import load_latest_version, try_load_meta
from cli_validator.result import CommandSource

logger = logging.getLogger(__name__)


class ExtensionLoader(BaseLoader):
    EXTENSION_COMMAND_TREE_URL = \
        'https://azurecliextensionsync.blob.core.windows.net/cmd-index/extensionCommandTree.json'

    def __init__(self, cache_dir: Optional[str] = './extension'):
        super().__init__(cache_dir)
        self.tree_path = os.path.join(self.cache_dir, 'ext_command_tree.json') if self.cache_dir else None

    def load(self):
        from cli_validator.loader.cmd_meta import load_http
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        raw_tree = load_http(self.EXTENSION_COMMAND_TREE_URL, self.tree_path, cache_strategy=CacheStrategy.Fallback)
        tree = json.loads(raw_tree)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)

    async def load_async(self):
        from cli_validator.loader.cmd_meta.aio import load_http
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        raw_tree = await load_http(self.EXTENSION_COMMAND_TREE_URL, self.tree_path,
                                   cache_strategy=CacheStrategy.Fallback)
        tree = json.loads(raw_tree)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)

    def _ext_meta_rel_uri(self, ext_name: str, version: Optional[str] = None):
        if not version:
            file_name = load_latest_version(self.cache_dir, ext_name)
        else:
            file_name = f'az_{ext_name}_meta_{version}.json'
        return f'azure-cli-extensions/ext-{ext_name}/{file_name}'

    def load_command_meta(self, signature: List[str], module: str):
        try:
            rel_uri = self._ext_meta_rel_uri(module, version=None)
        except requests.RequestException as e:
            logger.warning(f'{e} when retrieving versions of {module}')
            raise ExtensionNotFoundException(signature, module) from e
        meta = try_load_meta(rel_uri, self.cache_dir)
        if meta:
            try:
                for idx in range(len(signature) - 1):
                    meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
                return meta['commands'][' '.join(signature)]
            except KeyError as e:
                raise CommandMetaNotFoundException(signature) from e
        return None
