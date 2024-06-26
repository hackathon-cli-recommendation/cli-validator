import asyncio
import json
import logging
import os
import shutil
from typing import Optional

import httpx

from cli_validator.exceptions import VersionNotExistException
from cli_validator.loader import CacheStrategy
from cli_validator.loader.utils import load_from_local, store_to_local

BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
CONTAINER_NAME = 'cmd-metadata-per-version'

logger = logging.getLogger(__name__)


async def load_http(url: str, cache_path: Optional[str] = None,
                    cache_strategy: CacheStrategy = CacheStrategy.CacheAside, encoding: str = 'utf-8'):
    if cache_strategy == CacheStrategy.CacheAside and cache_path and os.path.exists(cache_path):
        return load_from_local(cache_path, encoding)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
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


async def load_version_index(target_dir: Optional[str] = None):
    cache_path = f'{target_dir}/version_list.txt' if target_dir else None
    data = await load_http(f'{BLOB_URL}/{CONTAINER_NAME}/version_list.txt', cache_path, CacheStrategy.Fallback)
    data = data.strip(' \n')
    return [v.strip() for v in data.split() if v.strip()]


async def load_latest_version(target_dir: Optional[str] = None):
    version_list = await load_version_index(target_dir)
    return version_list[-1]


async def try_load_meta(version_dir: str, file_name: str, target_dir: Optional[str] = None):
    cache_path = f'{target_dir}/{version_dir}/{file_name}' if target_dir else None
    try:
        meta = await load_http(f'{BLOB_URL}/{CONTAINER_NAME}/{version_dir}/{file_name}', cache_path)
        return json.loads(meta)
    except httpx.HTTPStatusError as e:
        logger.error(f'`{version_dir}/{file_name}` not Found', exc_info=e)
        return None
    except httpx.RequestError as e:
        logger.error(f'Error when loading `{version_dir}/{file_name}`', exc_info=e)
        return None
    except json.JSONDecodeError as e:
        logger.error(f'Error when parsing `{version_dir}/{file_name}`', exc_info=e)
        return None


async def load_meta_index(version_dir: str, target_dir: Optional[str] = './cmd_meta'):
    try:
        cache_path = f'{target_dir}/{version_dir}/index.txt' if target_dir else None
        index = await load_http(f'{BLOB_URL}/{CONTAINER_NAME}/{version_dir}/index.txt', cache_path,
                                cache_strategy=CacheStrategy.Fallback)
    except httpx.HTTPStatusError as e:
        raise VersionNotExistException(version_dir, 'Azure CLI') from e
    file_list = [f.strip() for f in index.strip(' \n').split()]
    return file_list


async def load_metas(version: Optional[str] = None, meta_dir: Optional[str] = './cmd_meta', force_refresh=False):
    """
    Load Command Metadata from local cache, fetch from Blob if not found
    :param version: version of `azure-cli` to be loaded
    :param meta_dir: root directory to cache Command Metadata
    :param force_refresh: load the metadata through network no matter whether there is a cache
    :return: list of command metadata
    """
    if not version:
        version_dir = await load_latest_version(meta_dir)
    else:
        version_dir = f'azure-cli-{version}'
    if meta_dir:
        if force_refresh and os.path.exists(f'{meta_dir}/{version_dir}'):
            shutil.rmtree(f'{meta_dir}/{version_dir}')
        os.makedirs(f'{meta_dir}/{version_dir}', exist_ok=True)
    files = []
    tasks = []
    for file_name in await load_meta_index(version_dir, meta_dir):
        files.append(file_name)
        tasks.append(asyncio.create_task(try_load_meta(version_dir, file_name, meta_dir)))
    metas = []
    if len(tasks) > 0:
        metas = await asyncio.gather(*tasks)
    metas = dict(zip(files, metas))
    metas = dict([(file_name, meta) for (file_name, meta) in metas.items() if meta is not None])
    if not metas:
        raise VersionNotExistException(version, 'Azure CLI')
    return metas
