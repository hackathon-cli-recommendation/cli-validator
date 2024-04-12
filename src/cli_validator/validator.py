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
from cli_validator.result import ValidationResult, CommandSetResult, CommandSetResultItem, CommandSource, \
    ScriptValidationItem
from cli_validator.script import iter_az_commands, idx_from_script


class CLIValidator(object):
    def __init__(self, cache_dir: Optional[str] = './cache'):
        core_repo_path = os.path.join(cache_dir, 'core_repo') if cache_dir else None
        extension_path = os.path.join(cache_dir, 'extension') if cache_dir else None
        self.core_repo_loader = CoreRepoLoader(core_repo_path)
        self.extension_loader = ExtensionLoader(extension_path)
        self.loaders: List[BaseLoader] = []

    def load_metas(self, version: Optional[str] = None, force_refresh=False):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        """
        self.core_repo_loader.load(version, force_refresh=force_refresh)
        self.extension_loader.load()
        self.loaders.extend([self.core_repo_loader, self.extension_loader])

    async def load_metas_async(self, version: Optional[str] = None, force_refresh=False):
        """
        Load command metadata through network or from local cache
        :param version: the version of Azure CLI from which the metadata is extracted
        :param force_refresh: force using the metadata on the network instead of local cache
        """
        import asyncio
        await asyncio.gather(
            self.core_repo_loader.load_async(version, force_refresh=force_refresh),
            self.extension_loader.load_async())
        self.loaders.extend([self.core_repo_loader, self.extension_loader])

    def validate_script(self, script: str, non_interactive=False, no_help=True) -> List[ScriptValidationItem]:
        """
        Validate all CLI commands in a script.
        Please note this method is under development and only support `$(...)` in assignment.
        :param script: to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return: a list of validated result
        """
        result = []
        try:
            for token_set in iter_az_commands(script):
                if not token_set:
                    continue
                tokens = [token.content for token in token_set]
                script_start = idx_from_script(script, token_set[0].lineno, token_set[0].col_pos)
                script_end = idx_from_script(script, token_set[-1].end_lineno, token_set[-1].end_col_pos)
                raw_command = script[script_start: script_end]
                validation_result = self._validate_command(raw_command, tokens, non_interactive, True, no_help)
                result.append(ScriptValidationItem(token_set[0].lineno, token_set[0].col_pos, token_set[-1].end_lineno,
                                                   token_set[-1].end_col_pos, validation_result))
            return result
        except ValidateFailureException as e:
            result.append([ScriptValidationItem(0, 0, 0, 0, ValidationResult.from_exception(e, script))])
            return result

    def validate_command(self, command: str, non_interactive=False, placeholder=True, no_help=True, comments=False):
        """
        Validate an input command
        :param command: to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder: allow placeholder like `<ResourceName>`, `$ResourceName` as field value
        :param no_help: reject commands with `--help`
        :param comments: parse comments in the given command
        :return: the validated result
        """
        try:
            if placeholder:
                command = re.sub(r' ((\$\([a-zA-Z0-9_ -.\[\]]*\))|(\${[a-zA-Z0-9_ -.\[\]]*})|'
                                 r'(<[a-zA-Z0-9_ ]*>)|(<<[a-zA-Z0-9_ -]*>>))', r' "\1"', command)
            tokens = shlex.split(command, comments)
        except ValueError as e:
            return ValidationResult(command, False, CommandSource.UNKNOWN, False,
                                    f'Fail to Parse command: {e}')
        return self._validate_command(command, tokens, non_interactive, placeholder, no_help)

    def _validate_command(self, command: str, tokens: List[str], non_interactive=False, placeholder=True, no_help=True):
        source = CommandSource.UNKNOWN
        try:
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
