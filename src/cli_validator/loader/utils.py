import logging

logger = logging.getLogger(__name__)


def load_from_local(cache_path: str, encoding='utf-8'):
    with open(cache_path, "r", encoding=encoding) as cache_file:
        return cache_file.read()


def store_to_local(data: str, cache_path: str, encoding='utf-8'):
    try:
        with open(cache_path, "w", encoding=encoding) as cache_file:
            cache_file.write(data)
    except FileNotFoundError as e:
        logger.warning("Cache File (%s) Not Found! ", cache_path, exc_info=e)
