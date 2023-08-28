import asyncio
import os

from azure.storage.blob.aio import BlobClient


BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
CONTAINER_NAME = 'cmd-metadata-per-version'


async def download_blob(url: str, target_path: str):
    blob = BlobClient.from_blob_url(url)
    with open(target_path, "wb") as my_blob:
        stream = await blob.download_blob()
        data = await stream.readall()
        my_blob.write(data)
    await blob.close()


async def _fetch_data(version: str, target_dir: str = './cmd_meta'):
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
            tasks.append(asyncio.create_task(download_blob(
                f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/{file_name}',
                f'{target_dir}/azure-cli-{version}/{file_name}')))
    await asyncio.wait(tasks)


if __name__ == "__main__":
    asyncio.run(_fetch_data("2.50.0"))
