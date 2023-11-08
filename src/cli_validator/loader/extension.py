import json
import os
from typing import Optional

import requests

from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.loader import BaseLoader
from cli_validator.result import CommandSource


class ExtensionLoader(BaseLoader):
    EXTENSION_COMMAND_TREE_URL = 'https://aka.ms/azExtCmdTree'

    def __init__(self, cache_dir: str = './extension'):
        super().__init__()
        self.cache_dir = cache_dir
        self.tree_path = os.path.join(self.cache_dir, 'ext_command_tree.json')

    def load(self, force_refresh=False):
        tree = load_from_disk(self.tree_path) if not force_refresh else None
        if not tree:
            fetch_command_tree(self.EXTENSION_COMMAND_TREE_URL, self.tree_path)
            tree = load_from_disk(self.tree_path)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)

    async def load_async(self, force_refresh=False):
        tree = load_from_disk(self.tree_path) if not force_refresh else None
        if not tree:
            await async_fetch_command_tree(self.EXTENSION_COMMAND_TREE_URL, self.tree_path)
            tree = load_from_disk(self.tree_path)
        self.command_tree = CommandTreeParser(tree, CommandSource.EXTENSION)


def fetch_command_tree(url: str, file_path: str):
    parent = os.path.dirname(file_path)
    if not os.path.exists(parent):
        os.makedirs(parent)
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)


async def async_fetch_command_tree(url: str, file_path: str):
    parent = os.path.dirname(file_path)
    if not os.path.exists(parent):
        os.makedirs(parent)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(await response.text('utf-8-sig'))


def load_from_disk(file_path: str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
