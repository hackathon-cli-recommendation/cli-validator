import json
import logging
import os
from typing import Optional

import requests

from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.loader import BaseLoader, CacheStrategy
from cli_validator.loader.utils import load_from_local, store_to_local
from cli_validator.result import CommandSource

logger = logging.getLogger(__name__)


class ExtensionLoader(BaseLoader):
    EXTENSION_COMMAND_TREE_URL = 'https://aka.ms/azExtCmdTree'

    def __init__(self, cache_dir: Optional[str] = './extension'):
        super().__init__()
        self.cache_dir = cache_dir
        self.tree_path = os.path.join(self.cache_dir, 'ext_command_tree.json') if self.cache_dir else None

    def load(self):
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        raw_tree = load_http(self.EXTENSION_COMMAND_TREE_URL, self.tree_path, cache_strategy=CacheStrategy.Fallback)
        tree = json.loads(raw_tree)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)

    async def load_async(self):
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        raw_tree = await async_load_http(self.EXTENSION_COMMAND_TREE_URL, self.tree_path,
                                         cache_strategy=CacheStrategy.Fallback)
        tree = json.loads(raw_tree)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)


def load_http(url: str, cache_path: Optional[str] = None, cache_strategy: CacheStrategy = CacheStrategy.CacheAside,
              encoding='utf-8'):
    if cache_strategy == CacheStrategy.CacheAside and cache_path and os.path.exists(cache_path):
        return load_from_local(cache_path, encoding)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.text
    except Exception as e:
        logger.error('Fail to Download File: %s', e, e)
        if cache_strategy == CacheStrategy.Fallback and cache_path and os.path.exists(cache_path):
            return load_from_local(cache_path, encoding)
        raise e from e
    if cache_path:
        store_to_local(data, cache_path, encoding)
    return data


async def async_load_http(url: str, cache_path: Optional[str] = None,
                          cache_strategy: CacheStrategy = CacheStrategy.CacheAside, encoding='utf-8'):
    import aiohttp
    if cache_strategy == CacheStrategy.CacheAside and cache_path and os.path.exists(cache_path):
        return load_from_local(cache_path, encoding)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.text('utf-8-sig')
    except Exception as e:
        logger.error('Fail to Download File: %s', e, e)
        if cache_strategy == CacheStrategy.Fallback and cache_path and os.path.exists(cache_path):
            return load_from_local(cache_path, encoding)
        raise e from e
    if cache_path:
        store_to_local(data, cache_path, encoding)
    return data
