from typing import List


class CommandInfo(object):
    def __init__(self, module, signature, parameters):
        self.module = module
        self.signature = signature
        self.parameters = parameters


class Result(object):
    def __init__(self, no_error: bool, msg=''):
        self.no_error = no_error
        self.msg = msg

    def __str__(self):
        if self.no_error:
            return 'No Error'
        else:
            return self.msg


class CommandSetResultItem(object):
    def __init__(self, command, result: Result, example_result: Result):
        self.signature = command.get('command')
        self.parameters = command.get('arguments')
        self.example = command.get('example')
        self.result = result
        self.example_result = example_result


class CommandSetResult(object):
    def __init__(self):
        self.items: List[CommandSetResultItem] = []
        self.errors: List[CommandSetResultItem] = []
        self.example_errors: List[CommandSetResultItem] = []

    def append(self, item: CommandSetResultItem):
        self.items.append(item)
        if not item.result.no_error:
            self.errors.append(item)
        if not item.example_result.no_error:
            self.example_errors.append(item)
