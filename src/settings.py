import os
from typing import Any


def get_env(key: str, default: Any) -> Any:
    """Gets value from OS environment
    infers data type from default to parse default string

    Args:
        key (str): Key of the environment value
        default (Any): Default value if value is not present in environment

    Returns:
        [Any]: Either the default or the environment value
    """
    env_value = os.getenv(key)
    if env_value:
        if type(default) == list:
            return env_value.split(',')
        elif type(default) == int:
            return int(env_value)
        elif type(default) == float:
            return float(env_value)
        return env_value
    return default


TABLE_BACKUP_DIRECTORY = get_env(
    'TABLE_BACKUP_DIRECTORY', 'table_backups')
REQUIRED_COLUMNS = get_env('REQUIRED_COLUMNS', ['title', 'year'])
OPTIONAL_COLUMNS = get_env(
    'OPTIONAL_COLUMNS', ['origin', 'imdb_id', 'imdb_link'])
NON_INTERACTIVE_MATCH_THRESHOLD = get_env(
    'NON_INTERACTIVE_MATCH_THRESHOLD', 95)
IMDB_LIST_LIMIT = get_env('IMDB_LIST_LIMIT', 10)
MATCH_LIST_LIMIT = get_env('MATCH_LIST_LIMIT', 10)
LOG_LEVEL = get_env('LOG_LEVEL', 'INFO')
