import os
import re
import shlex
from typing import List

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.exceptions import UnknownCommandException, ValidateFailureException
from cli_validator.result import FailureInfo, CommandSetResult, CommandSetResultItem


class CLIValidator(object):
    def __init__(self, cache_path: str = './cache'):
        self.cmd_meta_validator = CommandMetaValidator(os.path.join(cache_path, 'cmd_meta'))
        self.ext_command_tree = CommandTreeParser.load('https://aka.ms/azExtCmdTree',
                                                       os.path.join(cache_path, 'ext_command_tree.json'))

    def load_metas(self, version: str, force_refresh=False):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        """
        self.cmd_meta_validator.load_metas(version, force_refresh=force_refresh)

    async def load_metas_async(self, version: str, force_refresh=False):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        """
        await self.cmd_meta_validator.load_metas_async(version, force_refresh=force_refresh)

    def validate_command(self, command: str, non_interactive=False, placeholder=True, no_help=True, comments=False):
        """
        Validate an input command
        :param command: to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder: allow placeholder like `<ResourceName>`, `$ResourceName` as field value
        :param no_help: reject commands with `--help`
        :param comments: parse comments in the given command
        :return: the failure info if command is invalid, else `None`
        """
        try:
            try:
                if placeholder:
                    command = re.sub(r' ((\$\([a-zA-Z0-9_ -.\[\]]*\))|'
                                     r'(\${[a-zA-Z0-9_ -.\[\]]*})|'
                                     r'(<[a-zA-Z0-9_ ]*>)|'
                                     r'(<<[a-zA-Z0-9_ -]*>>))',
                                     r' "\1"', command)
                tokens = shlex.split(command, comments)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            try:
                self.cmd_meta_validator.validate_command(tokens, non_interactive, placeholder, no_help)
            except UnknownCommandException:
                self.ext_command_tree.parse_command(tokens)
        except ValidateFailureException as e:
            return FailureInfo.from_exception(e, command)
        return None

    def validate_sig_params(self, signature: str, parameters: List[str], non_interactive=False, no_help=True):
        """
        Validate a command signature and parameters used with it
        :param signature: signature to be validated
        :param parameters: parameter key list
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return: the failure info if command is invalid, else `None`
        """
        try:
            try:
                tokens = shlex.split(signature)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            try:
                self.cmd_meta_validator.validate_sig_params(tokens, parameters, non_interactive, no_help)
            except UnknownCommandException:
                self.ext_command_tree.parse_command(tokens)
        except ValidateFailureException as e:
            return FailureInfo.from_exception(e, '{} {}'.format(signature, ' '.join(parameters)))
        return None

    def validate_command_set(self, command_set, non_interactive=False, no_help=True):
        """
        Validate a Command Set with command and example
        :param command_set: a CommandSet is a list of command item. Each command item contains a `command` field,
            a `argument` field and an `example` field
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return: a commandSetResult that contains the failure details of each command
        """
        result = CommandSetResult()
        for command in command_set:
            item = CommandSetResultItem(command)
            if "command" in command:
                item.result = self.validate_sig_params(
                    command["command"], command.get("arguments", []), non_interactive, no_help)
            if "example" in command:
                item.example_result = self.validate_command(command["example"], non_interactive, no_help)
            result.append(item)
        return result
