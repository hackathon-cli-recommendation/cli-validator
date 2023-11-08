from enum import Enum
from typing import Optional, List

from cli_validator.exceptions import ValidateFailureException


class CommandSource(str, Enum):
    UNKNOWN = "Unknown Source"
    CORE_MODULE = "Core Module"
    EXTENSION = "Extension"


class ValidationResult:
    def __init__(self, command: str, is_valid: bool, source: CommandSource, validated_param=True,
                 error_message: Optional[str] = None):
        self.command = command
        self.is_valid = is_valid
        self.cmd_source = source
        self.validated_param = validated_param
        self.error_message = error_message

    @staticmethod
    def from_exception(e: ValidateFailureException, command: str, source: CommandSource = CommandSource.UNKNOWN):
        return ValidationResult(command, False, source, error_message=e.msg)

    def __str__(self):
        if self.is_valid:
            return f"The command is valid and belongs to the {self.cmd_source}."
        else:
            return f"The command is invalid. {self.error_message}"


class CommandSetResultItem(object):
    def __init__(self, command):
        self.signature = command.get('command')
        self.parameters = command.get('arguments')
        self.example = command.get('example')
        self.result: Optional[ValidationResult] = None
        self.example_result: Optional[ValidationResult] = None


class CommandSetResult(object):
    def __init__(self):
        self.items: List[CommandSetResultItem] = []
        self.errors: List[CommandSetResultItem] = []
        self.example_errors: List[CommandSetResultItem] = []

    def append(self, item: CommandSetResultItem):
        self.items.append(item)
        if item.result and not item.result.is_valid:
            self.errors.append(item)
        if item.example_result and not item.example_result.is_valid:
            self.example_errors.append(item)
