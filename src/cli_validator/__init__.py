import shlex
from typing import List, Optional

from cli_validator.exceptions import UnmatchedBracketsException


class CommandInfo(object):
    BRACKETS = {
        '$(': ')',
        '${': '}',
        '(': ')',
        '{': '}',
    }

    def __init__(self, module, signature, parameters: List[str]):
        self.module = module
        self.signature = signature
        self._parameters = parameters
        self.parameters = []
        self.sub_commands = list(self._sub_expressions())

    def _sub_expressions(self):
        brackets = []
        cur = []
        for param in self._parameters:
            for bracket in self.BRACKETS:
                if param.startswith(bracket):
                    brackets.append((param, bracket, self.BRACKETS[bracket]))
                    break
            if len(brackets) > 0:
                cur.append(param)
            else:
                self.parameters.append(param)
            if param[-1] in self.BRACKETS.values():
                if len(brackets) == 0:
                    raise UnmatchedBracketsException(self._parameters[0], param)
                elif param[-1] != brackets[-1][2]:
                    raise UnmatchedBracketsException(brackets[-1][0], param)
                else:
                    bracket = brackets.pop()
                    if len(brackets) == 0:
                        if bracket[1][0] == '$':
                            self.parameters.append(' '.join(cur))
                            cur[0] = cur[0][len(bracket[1]):]
                            cur[-1] = cur[-1][:-len(bracket[2])]
                            # yield shlex.join(cur)
                            yield ' '.join(cur)
                            cur = []
                        else:
                            self.parameters.extend(cur)
        if len(brackets) > 0:
            raise UnmatchedBracketsException(brackets[0][0], self._parameters[-1])


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
    def __init__(self, command):
        self.signature = command.get('command')
        self.parameters = command.get('arguments')
        self.example = command.get('example')
        self.result: Optional[Result] = None
        self.example_result: Optional[Result] = None


class CommandSetResult(object):
    def __init__(self):
        self.items: List[CommandSetResultItem] = []
        self.errors: List[CommandSetResultItem] = []
        self.example_errors: List[CommandSetResultItem] = []

    def append(self, item: CommandSetResultItem):
        self.items.append(item)
        if item.result and not item.result.no_error:
            self.errors.append(item)
        if item.example_result and not item.example_result.no_error:
            self.example_errors.append(item)
