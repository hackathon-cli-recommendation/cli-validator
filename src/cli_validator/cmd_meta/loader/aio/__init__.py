import asyncio
import json
import logging
import os
from json import JSONDecodeError

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobClient

from cli_validator.cmd_meta.loader import ResourceNotExistException

BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
CONTAINER_NAME = 'cmd-metadata-per-version'

logger = logging.getLogger(__name__)


async def download_blob(url: str, target_path: str):
    blob = BlobClient.from_blob_url(url)
    try:
        with open(target_path, "wb") as my_blob:
            stream = await blob.download_blob()
            data = await stream.readall()
            my_blob.write(data)
    except ResourceNotFoundError as e:
        raise ResourceNotExistException(e.message)
    finally:
        await blob.close()


async def try_download_meta(version: str, file_name: str, target_dir: str):
    try:
        await download_blob(f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/{file_name}',
                            f'{target_dir}/azure-cli-{version}/{file_name}')
    except ResourceNotExistException as e:
        logger.error(f'`azure-cli-{version}/{file_name}` not Found')


async def fetch_metas(version: str, target_dir: str = './cmd_meta'):
    # TODO: fix `RuntimeError: Event loop is closed`
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    if not os.path.exists(f'{target_dir}/azure-cli-{version}'):
        os.mkdir(f'{target_dir}/azure-cli-{version}')
    await download_blob(f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/index.txt',
                        f'{target_dir}/azure-cli-{version}/index.txt')
    tasks = []
    with open(f'{target_dir}/azure-cli-{version}/index.txt', 'r', encoding='utf-8') as f:
        for file_name in f.readlines():
            file_name = file_name.strip(' \n')
            tasks.append(asyncio.create_task(try_download_meta(version, file_name, target_dir)))
    if len(tasks) > 0:
        await asyncio.wait(tasks)


if __name__ == "__main__":
    asyncio.run(fetch_metas("2.51.0"))
