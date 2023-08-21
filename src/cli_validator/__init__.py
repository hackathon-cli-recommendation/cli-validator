import os
from typing import List

from cli_validator.cmd_meta import CommandValidatorWithMeta
from cli_validator.result import Result


class CLIValidator(object):
    def __init__(self, version: str, cache_path: str = './cache'):
        self.cmd_meta_validator = CommandValidatorWithMeta(version, os.path.join(cache_path, 'cmd_meta'))

    def validate(self, cmds: List[str]) -> List[Result]:
        return [self.cmd_meta_validator.validate_command(cmd) for cmd in cmds]
