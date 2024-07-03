import json
import logging

import httpx

from cli_validator.cmd_tree import CommandSource, CommandTreeParser
from cli_validator.exceptions import CommandTreeRetrieveException, MetadataRetrieveException, \
    VersionListRetrieveException, EmptyVersionListException

logger = logging.getLogger(__name__)


async def retrieve_http(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.text
    return data


async def retrieve_command_tree(url: str, source: CommandSource, retry=3):
    while True:
        try:
            raw_tree = await retrieve_http(url)
            return CommandTreeParser(json.loads(raw_tree), source)
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.error("Fail to Retrieve Command Tree.", exc_info=e)
            retry -= 1
            if retry <= 0:
                raise CommandTreeRetrieveException(source) from e
            logger.error("Retrying...")


async def retrieve_meta(url: str, retry=3):
    while True:
        try:
            raw_meta = await retrieve_http(url)
            return json.loads(raw_meta)
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.error("Fail to Retrieve Command Tree.", exc_info=e)
            retry -= 1
            if retry <= 0:
                raise MetadataRetrieveException() from e
            logger.error("Retrying...")


async def retrieve_list(url: str, retry=3):
    while True:
        try:
            data = await retrieve_http(url)
            data = data.strip(' \n')
            return [v.strip() for v in data.split() if v.strip()]
        except httpx.HTTPError as e:
            logger.error("Fail to Retrieve Version List.", exc_info=e)
            retry -= 1
            if retry <= 0:
                raise VersionListRetrieveException() from e
            logger.error("Retrying...")


async def retrieve_latest_version(url: str, retry=3):
    version_list = await retrieve_list(url, retry)
    if not version_list:
        raise EmptyVersionListException()
    return version_list[-1]
