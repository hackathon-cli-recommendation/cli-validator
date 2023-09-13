import os
from typing import List

from cli_validator import Result, CommandSetResult, CommandSetResultItem
from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.cmd_tree import parse_command
from cli_validator.cmd_tree.loader import load_command_tree
from cli_validator.exceptions import UnknownCommandException, ValidateFailureException


class CLIValidator(object):
    def __init__(self, cache_path: str = './cache'):
        self.cmd_meta_validator = CommandMetaValidator(os.path.join(cache_path, 'cmd_meta'))
        self.ext_command_tree = load_command_tree('https://aka.ms/azExtCmdTree',
                                                  os.path.join(cache_path, 'ext_command_tree.json'))

    def load_metas(self, version: str):
        self.cmd_meta_validator.load_metas(version)

    async def load_metas_async(self, version: str):
        await self.cmd_meta_validator.load_metas_async(version)

    def validate_command(self, command, non_interactive=False, placeholder=True, no_help=True, comments=True):
        """
        Validate an input command
        :param command: to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder:
        :param no_help: reject commands with `--help`
        :param comments: parse comments in the given command
        :return:
        """
        try:
            try:
                self.cmd_meta_validator.validate_command(command, non_interactive, placeholder, no_help, comments)
            except UnknownCommandException:
                parse_command(self.ext_command_tree, command, comments)
        except ValidateFailureException as e:
            return Result(False, e.msg)
        return Result(True)

    def validate_separate_command(self, command_signature, parameters, non_interactive=False, no_help=True):
        """
        Validate an input command
        :param command_signature: signature to be validated
        :param parameters: parameter key list
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return:
        """
        try:
            try:
                self.cmd_meta_validator.validate_separate_command(
                    command_signature, parameters, non_interactive, no_help)
            except UnknownCommandException:
                parse_command(self.ext_command_tree, command_signature, False)
        except ValidateFailureException as e:
            return Result(False, e.msg)
        return Result(True)

    def validate(self, commands: List[str]):
        return [self.validate_command(cmd) for cmd in commands]

    def validate_command_set(self, command_set, non_interactive=False, no_help=True):
        result = CommandSetResult()
        for command in command_set:
            result.append(CommandSetResultItem(
                command,
                self.validate_separate_command(command["command"], command["arguments"], non_interactive, no_help),
                self.validate_command(command["example"], non_interactive, no_help)))
        return result
