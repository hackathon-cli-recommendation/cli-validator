import concurrent.futures
import json
import logging
import os
import shutil
from typing import Optional

import requests

from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.exceptions import VersionNotExistException
from cli_validator.loader import CacheStrategy
from cli_validator.loader.utils import load_from_local, store_to_local

BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
CONTAINER_NAME = 'cmd-metadata-per-version'

logger = logging.getLogger(__name__)


def load_blob_text(url: str, cache_path: Optional[str] = None, cache_strategy: CacheStrategy = CacheStrategy.CacheAside,
                   encoding: str = 'utf-8'):
    if cache_strategy == CacheStrategy.CacheAside and cache_path and os.path.exists(cache_path):
        return load_from_local(cache_path, encoding)
    try:
        resp = requests.get(url, params=None)
        resp.raise_for_status()
        data = resp.text
    except Exception as e:
        logger.error("Fail to Download Blob", exc_info=e)
        if cache_strategy == CacheStrategy.Fallback and cache_path and os.path.exists(cache_path):
            return load_from_local(cache_path, encoding)
        raise e from e
    if cache_path:
        store_to_local(data, cache_path, encoding)
    return data


def load_version_index(target_dir: Optional[str] = None, ext_name: Optional[str] = None):
    ext_sep = f'/azure-cli-extensions/ext-{ext_name}' if ext_name else ''
    cache_path = f'{target_dir}{ext_sep}/version_list.txt' if target_dir else None
    data = load_blob_text(f'{BLOB_URL}/{CONTAINER_NAME}{ext_sep}/version_list.txt', cache_path, CacheStrategy.Fallback)
    data = data.strip(' \n')
    return [v.strip() for v in data.split() if v.strip()]


def load_latest_version(target_dir: Optional[str] = None, ext_name: Optional[str] = None):
    version_list = load_version_index(target_dir, ext_name=ext_name)
    return version_list[-1]


def try_load_meta(rel_uri: str, target_dir: Optional[str] = None):
    cache_path = f'{target_dir}/{rel_uri}' if target_dir else None
    try:
        meta = load_blob_text(f'{BLOB_URL}/{CONTAINER_NAME}/{rel_uri}', cache_path)
        return json.loads(meta)
    except requests.HTTPError as e:
        logger.error(f'`{rel_uri}` not Found', exc_info=e)
        return None
    except json.JSONDecodeError as e:
        logger.error(f'Error when parsing `{rel_uri}`', exc_info=e)
        return None


def try_load_core_meta(version_dir: str, file_name: str, target_dir: Optional[str] = None):
    return try_load_meta(f'{version_dir}/{file_name}', target_dir)


def load_meta_index(version_dir: str, target_dir: Optional[str] = './cmd_meta'):
    try:
        cache_path = f'{target_dir}/{version_dir}/index.txt' if target_dir else None
        index = load_blob_text(f'{BLOB_URL}/{CONTAINER_NAME}/{version_dir}/index.txt', cache_path,
                               cache_strategy=CacheStrategy.Fallback)
    except requests.HTTPError as e:
        raise VersionNotExistException(version_dir, 'Azure CLI') from e
    file_list = [f.strip() for f in index.strip(' \n').split()]
    return file_list


def load_core_metas(version: Optional[str] = None, meta_dir: Optional[str] = './cmd_meta', force_refresh=False):
    """
    Load Command Metadata from local cache, fetch from Blob if not found
    :param version: version of `azure-cli` to be loaded
    :param meta_dir: root directory to cache Command Metadata
    :param force_refresh: load the metadata through network no matter whether there is a cache
    :return: list of command metadata
    """
    if not version:
        version_dir = load_latest_version(meta_dir)
    else:
        version_dir = f'azure-cli-{version}'
    if meta_dir:
        if force_refresh and os.path.exists(f'{meta_dir}/{version_dir}'):
            shutil.rmtree(f'{meta_dir}/{version_dir}')
        os.makedirs(f'{meta_dir}/{version_dir}', exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        file_names = load_meta_index(version_dir, meta_dir)
        metas = executor.map(lambda file_name: try_load_core_meta(version_dir, file_name, meta_dir), file_names)
        metas = dict(zip(file_names, metas))
        metas = dict([(file_name, meta) for (file_name, meta) in metas.items() if meta is not None])
    if not metas:
        raise VersionNotExistException(version, 'Azure CLI')
    return metas


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
