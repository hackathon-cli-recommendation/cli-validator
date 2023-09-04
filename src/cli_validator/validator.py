import os

from cli_validator import Result
from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.cmd_tree import parse_command
from cli_validator.cmd_tree.loader import load_command_tree
from cli_validator.exceptions import UnknownCommandException, ValidateFailureException


class CLIValidator(object):
    def __init__(self, version: str, cache_path: str = './cache'):
        self.cmd_meta_validator = CommandMetaValidator(version, os.path.join(cache_path, 'cmd_meta'))
        self.ext_command_tree = load_command_tree('https://aka.ms/azExtCmdTree',
                                                  os.path.join(cache_path, 'ext_command_tree.json'))

    def validate_command(self, command, comments=True):
        try:
            try:
                self.cmd_meta_validator.validate_command(command, comments)
            except UnknownCommandException:
                parse_command(self.ext_command_tree, command, comments)
        except ValidateFailureException as e:
            return Result(False, e.msg)
        return Result(True)

    def validate(self, commands):
        return [self.validate_command(cmd) for cmd in commands]
