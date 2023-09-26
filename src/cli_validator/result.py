from typing import Optional, List

from cli_validator.exceptions import ValidateFailureException


class FailureInfo(object):
    def __init__(self, msg: str, command: Optional[str] = None):
        self.msg = msg
        self.command = command

    @staticmethod
    def from_exception(e: ValidateFailureException, command: str):
        return FailureInfo(e.msg, command)

    def __str__(self):
        return 'Failure ({}): \t{}'.format(self.command, self.msg)


class CommandSetResultItem(object):
    def __init__(self, command):
        self.signature = command.get('command')
        self.parameters = command.get('arguments')
        self.example = command.get('example')
        self.result: Optional[FailureInfo] = None
        self.example_result: Optional[FailureInfo] = None


class CommandSetResult(object):
    def __init__(self):
        self.items: List[CommandSetResultItem] = []
        self.errors: List[CommandSetResultItem] = []
        self.example_errors: List[CommandSetResultItem] = []

    def append(self, item: CommandSetResultItem):
        self.items.append(item)
        if item.result:
            self.errors.append(item)
        if item.example_result:
            self.example_errors.append(item)
