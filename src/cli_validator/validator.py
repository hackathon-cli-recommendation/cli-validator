import os
import re
import shlex
from typing import List, Optional

from cli_validator.loader import BaseLoader
from cli_validator.loader.core_repo import CoreRepoLoader
from cli_validator.loader.extension import ExtensionLoader
from cli_validator.meta.validator import CommandMetaValidator
from cli_validator.exceptions import UnknownCommandException, ValidateFailureException, ValidateHelpException, \
    CommandMetaNotFoundException, MissingSubCommandException, TooLongSignatureException
from cli_validator.result import ValidationResult, CommandSetResult, CommandSetResultItem, CommandSource


class CLIValidator(object):
    def __init__(self, cache_dir: str = './cache'):
        self.core_repo_loader = CoreRepoLoader(os.path.join(cache_dir, 'core_repo'))
        self.extension_loader = ExtensionLoader(os.path.join(cache_dir, 'extension'))
        self.loaders: List[BaseLoader] = []

    def load_metas(self, version: Optional[str] = None, force_refresh=False, version_refresh=True):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        :param version_refresh: load the version index no matter whether there is a cache
        """
        self.core_repo_loader.load(version, force_refresh=force_refresh, version_refresh=version_refresh)
        self.extension_loader.load(force_refresh=version_refresh)
        self.loaders.extend([self.core_repo_loader, self.extension_loader])

    async def load_metas_async(self, version: Optional[str] = None, force_refresh=False, version_refresh=True):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        :param version_refresh: load the version index no matter whether there is a cache
        """
        import asyncio
        await asyncio.gather(
            self.core_repo_loader.load_async(version, force_refresh=force_refresh, version_refresh=version_refresh),
            self.extension_loader.load_async(force_refresh=version_refresh))
        self.loaders.extend([self.core_repo_loader, self.extension_loader])

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
        source = CommandSource.UNKNOWN
        try:
            try:
                if placeholder:
                    command = re.sub(r' ((\$\([a-zA-Z0-9_ -.\[\]]*\))|(\${[a-zA-Z0-9_ -.\[\]]*})|'
                                     r'(<[a-zA-Z0-9_ ]*>)|(<<[a-zA-Z0-9_ -]*>>))', r' "\1"', command)
                tokens = shlex.split(command, comments)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            for loader in self.loaders:
                try:
                    cmd_info = loader.command_tree.parse_command(tokens)
                    source = loader.command_tree.source
                    if cmd_info.module is None:
                        return handle_help(no_help, command, source)
                    meta = loader.load_command_meta(cmd_info.signature, cmd_info.module)
                    if meta is None:
                        raise CommandMetaNotFoundException(cmd_info.signature)
                    validator = CommandMetaValidator(meta)
                    validator.validate_params(cmd_info.parameters, non_interactive, placeholder, no_help)
                    return ValidationResult(command, True, source)
                except UnknownCommandException:
                    continue
            raise UnknownCommandException(command)
        except CommandMetaNotFoundException:
            return ValidationResult(command, True, source, validated_param=False)
        except ValidateFailureException as e:
            return ValidationResult.from_exception(e, command, source)

    def validate_sig_params(self, signature: str, parameters: List[str], non_interactive=False, no_help=True):
        """
        Validate a command signature and parameters used with it
        :param signature: signature to be validated
        :param parameters: parameter key list
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return: the failure info if command is invalid, else `None`
        """
        source = CommandSource.UNKNOWN
        command = '{} {}'.format(signature, ' '.join(parameters))
        try:
            try:
                tokens = shlex.split(signature)
            except ValueError as e:
                raise ValidateFailureException(str(e)) from e
            for loader in self.loaders:
                try:
                    try:
                        cmd_info = loader.command_tree.parse_command(tokens)
                        if cmd_info.module is None:
                            return handle_help(no_help, command, source, e=ValidateHelpException())
                    except MissingSubCommandException as e:
                        if len(parameters) == 1 and parameters[0] in ['-h', '--help']:
                            return handle_help(no_help, command, source, e=ValidateHelpException())
                        else:
                            raise e
                    if cmd_info.parameters:
                        raise TooLongSignatureException(signature, 'az ' + shlex.join(cmd_info.signature))
                    source = loader.command_tree.source
                    if cmd_info.module is None and no_help:
                        raise ValidateHelpException()
                    meta = loader.load_command_meta(cmd_info.signature, cmd_info.module)
                    if meta is None:
                        raise CommandMetaNotFoundException(cmd_info.signature)
                    validator = CommandMetaValidator(meta)
                    validator.validate_param_keys(parameters, non_interactive, no_help)
                    return ValidationResult(command, True, source)
                except TooLongSignatureException as e:
                    raise e from e
                except UnknownCommandException:
                    continue
            raise UnknownCommandException(signature)
        except CommandMetaNotFoundException:
            return ValidationResult(command, True, source, validated_param=False)
        except ValidateFailureException as e:
            return ValidationResult.from_exception(e, command, source)

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


def handle_help(no_help, command, source, e=None):
    if no_help:
        raise ValidateHelpException() from e
    return ValidationResult(command, True, source, validated_param=False)
