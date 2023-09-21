import os
import shlex
from typing import List

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.cmd_tree.loader import load_command_tree
from cli_validator.exceptions import UnknownCommandException, ValidateFailureException
from cli_validator.result import FailureInfo, CommandSetResult, CommandSetResultItem


class CLIValidator(object):
    def __init__(self, cache_path: str = './cache'):
        self.cmd_meta_validator = CommandMetaValidator(os.path.join(cache_path, 'cmd_meta'))
        self.ext_command_tree = load_command_tree('https://aka.ms/azExtCmdTree',
                                                  os.path.join(cache_path, 'ext_command_tree.json'))

    def load_metas(self, version: str):
        self.cmd_meta_validator.load_metas(version)

    async def load_metas_async(self, version: str):
        await self.cmd_meta_validator.load_metas_async(version)

    def validate_command(self, command: str, non_interactive=False, placeholder=True, no_help=True, comments=True):
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
                tokens = shlex.split(command)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            try:
                self.cmd_meta_validator.validate_command(tokens, non_interactive, placeholder, no_help)
            except UnknownCommandException:
                self.ext_command_tree.parse_command(tokens)
        except ValidateFailureException as e:
            return FailureInfo.from_exception(e, command)
        return None

    def validate_separate_command(self, signature: str, parameters: List[str], non_interactive=False, no_help=True):
        """
        Validate an input command
        :param signature: signature to be validated
        :param parameters: parameter key list
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return:
        """
        try:
            try:
                tokens = shlex.split(signature)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            try:
                self.cmd_meta_validator.validate_separate_command(tokens, parameters, non_interactive, no_help)
            except UnknownCommandException:
                self.ext_command_tree.parse_command(tokens)
        except ValidateFailureException as e:
            return FailureInfo.from_exception(e, '{} {}'.format(signature, ' '.join(parameters)))
        return None

    def validate(self, commands: List[str]):
        return [self.validate_command(cmd) for cmd in commands]

    def validate_command_set(self, command_set, non_interactive=False, no_help=True):
        result = CommandSetResult()
        for command in command_set:
            item = CommandSetResultItem(command)
            if "command" in command:
                item.result = self.validate_separate_command(
                    command["command"], command.get("arguments", []), non_interactive, no_help)
            if "example" in command:
                item.example_result = self.validate_command(command["example"], non_interactive, no_help)
            result.append(item)
        return result
