import asyncio
import re
import shlex
from typing import List, Optional

from cli_validator.meta import CommandMetaValidator, MetaRetrieverFactory, MetaRetriever
from cli_validator.exceptions import (ValidateException, ValidateHelpException, MissingSubCommandException,
                                      TooLongSignatureException, CommandTreeException, ScriptParseException)
from cli_validator.result import ValidationResult, CommandSetResult, CommandSetResultItem, CommandSource, \
    ScriptValidationItem
from cli_validator.script import iter_az_commands, idx_from_script, _Token


class CLIValidator(object):
    """
    A Validator that dynamically loads metadata from Azure CLI’s blob storage.

    **Note:** A `CLIValidator` retains the same metadata across different function calls.
    If a `CLIValidator` is created and used with Azure CLI version 2.59.0,
    it will continue to use the old metadata even after Azure CLI 2.60.0 is released.
    """
    META_RETRIEVER_FACTORY = MetaRetrieverFactory()

    def __init__(self, meta_retriever: Optional[MetaRetriever] = None):
        self.meta_retriever = meta_retriever or self.META_RETRIEVER_FACTORY.retriever

    async def _validate_script_token_set(self, token_set: List[_Token], script: str, non_interactive=False,
                                         no_help=True) -> ScriptValidationItem:
        tokens = [token.content for token in token_set]
        script_start = idx_from_script(script, token_set[0].lineno, token_set[0].col_pos)
        script_end = idx_from_script(script, token_set[-1].end_lineno, token_set[-1].end_col_pos)
        raw_command = script[script_start: script_end]
        validation_result = await self._validate_command(raw_command, tokens, non_interactive, True, no_help)
        return ScriptValidationItem(token_set[0].lineno, token_set[0].col_pos, token_set[-1].end_lineno,
                                    token_set[-1].end_col_pos, validation_result)

    async def validate_script(self, script: str, non_interactive=False, no_help=True) -> List[ScriptValidationItem]:
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
            tasks = [self._validate_script_token_set(token_set, script, non_interactive, no_help)
                     for token_set in iter_az_commands(script)]
            result = list(await asyncio.gather(*tasks))
            return result
        except ScriptParseException as e:
            lines = script.splitlines()
            end_lineno = len(lines) - 1 if lines else 0
            end_col_pos = len(lines[-1]) if lines else 0
            result.append(ScriptValidationItem(0, 0, end_lineno, end_col_pos, ValidationResult.from_exception(e, script)))
            return result

    async def validate_command(self, command: str, non_interactive=False, placeholder=True, no_help=True, comments=False):
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
        return await self._validate_command(command, tokens, non_interactive, placeholder, no_help)

    async def _validate_command(self, command: str, tokens: List[str], non_interactive=False, placeholder=True,
                                no_help=True):
        source = CommandSource.UNKNOWN
        try:
            cmd_meta = await self.meta_retriever.retrieve_meta(tokens)
            source = cmd_meta.source
            if cmd_meta.is_help:
                return handle_help(no_help, command, source)
            if cmd_meta.metadata is None:
                return ValidationResult(command, True, source, validated_param=False)
            validator = CommandMetaValidator(cmd_meta.metadata)
            validator.validate_params(cmd_meta.parameters, non_interactive, placeholder, no_help)
            return ValidationResult(command, True, source)
        except (CommandTreeException, ValidateException) as e:
            return ValidationResult.from_exception(e, command, source)

    async def validate_sig_params(self, signature: str, parameters: List[str], non_interactive=False, no_help=True):
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
                raise ValidateException(str(e)) from e

            try:
                cmd_meta = await self.meta_retriever.retrieve_meta(tokens)
                if cmd_meta.is_help:
                    return handle_help(no_help, command, source, e=ValidateHelpException())
            except MissingSubCommandException as e:
                if len(parameters) == 1 and parameters[0] in ['-h', '--help']:
                    return handle_help(no_help, command, source, e=ValidateHelpException())
                else:
                    raise e
            if cmd_meta.parameters:
                raise TooLongSignatureException(signature, 'az ' + shlex.join(cmd_meta.signature))

            source = cmd_meta.source
            if cmd_meta.metadata is None:
                return ValidationResult(command, True, source, validated_param=False)
            validator = CommandMetaValidator(cmd_meta.metadata)
            validator.validate_param_keys(parameters, non_interactive, no_help)
            return ValidationResult(command, True, source)
        except (CommandTreeException, ValidateException) as e:
            return ValidationResult.from_exception(e, command, source)

    async def _validate_command_set_item(self, command, non_interactive=False, no_help=True):
        item = CommandSetResultItem(command)
        if "command" in command:
            item.result = await self.validate_sig_params(
                command["command"], command.get("arguments", []), non_interactive, no_help)
        if "example" in command:
            item.example_result = await self.validate_command(command["example"], non_interactive, no_help)
        return item

    async def validate_command_set(self, command_set, non_interactive=False, no_help=True):
        """
        Validate a Command Set with command and example
        :param command_set: a CommandSet is a list of command item. Each command item contains a `command` field,
            a `argument` field and an `example` field
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :return: a commandSetResult that contains the failure details of each command
        """
        result = CommandSetResult()
        tasks = [self._validate_command_set_item(command, non_interactive, no_help) for command in command_set]
        for item in await asyncio.gather(*tasks):
            result.append(item)
        return result


def handle_help(no_help, command, source, e=None):
    if no_help:
        raise ValidateHelpException() from e
    return ValidationResult(command, True, source, validated_param=False)
