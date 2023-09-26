import json
import os

import requests


def fetch_command_tree(url: str, file_path: str):
    parent = os.path.dirname(file_path)
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(requests.get(url).text)


def load_from_disk(file_path: str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_command_tree(url: str, file_path: str):
    tree = load_from_disk(file_path)
    if not tree:
        fetch_command_tree(url, file_path)
        tree = load_from_disk(file_path)
    return tree
