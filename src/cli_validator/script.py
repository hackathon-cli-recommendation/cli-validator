import re
import shlex
from dataclasses import dataclass
from typing import List

from cli_validator.exceptions import ScriptParseException


def idx_from_script(script: str, lineno: int, col_pos: int):
    lines = script.splitlines(keepends=True)
    if lineno < len(lines):
        line_start_index = sum(len(lines[i]) for i in range(lineno))
        if col_pos <= len(lines[lineno]):
            return line_start_index + col_pos
    raise IndexError((script, lineno, col_pos))


@dataclass
class _Token:
    content: str
    raw: str
    lineno: int
    col_pos: int
    end_lineno: int
    end_col_pos: int

    def split_from(self, pos: int):
        return _Token(self.content[pos:], self.raw[pos:], self.lineno, self.col_pos + pos, self.end_lineno,
                      self.end_col_pos)

    def split_to(self, pos_from_right: int):
        return _Token(self.content[:-pos_from_right], self.raw[:-pos_from_right], self.lineno, self.col_pos,
                      self.end_lineno, self.end_col_pos - pos_from_right)

    def merge(self, other, script: str):
        start = idx_from_script(script, self.lineno, self.col_pos)
        end = idx_from_script(script, other.end_lineno, other.end_col_pos)
        return _Token(script[start: end].strip('\'"'), script[start: end], self.lineno,
                      self.col_pos, other.end_lineno, other.end_col_pos)


def _split_with_pos(line: str, lineno=0):
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    while True:
        col_pos = lexer.instream.tell()
        token = lexer.get_token()
        if token == lexer.eof:
            break
        next_col_pos = lexer.instream.tell()
        end_col_pos = len(line[:next_col_pos].rstrip())
        yield _Token(token, line[col_pos:end_col_pos], lineno, col_pos, lineno, end_col_pos)


def extract_token_sets_from_script(script: str):
    command_parts = []
    parenthesis_left = re.compile(r'^[a-zA-Z0-9-_=$]*\(')
    parenthesis_right = re.compile(r'(\);*)+$')

    for lineno, line in enumerate(script.splitlines()):
        if line.endswith('\\'):
            line = line[:-1]
            command_parts.extend(_split_with_pos(line, lineno))
            continue

        command_parts.extend(_split_with_pos(line, lineno))
        command_token_set = []
        token_set_stack: List[List[_Token]] = []
        if command_parts:
            for token in command_parts:
                if token_set_stack:
                    if command_token_set:
                        command_token_set[-1] = command_token_set[-1].merge(token, script)
                    else:
                        command_token_set.append(token)
                    token_set_stack[-1].append(token)
                    for token_set in token_set_stack[:-1]:
                        if token_set:
                            token_set[-1] = token_set[-1].merge(token, script)
                        else:
                            token_set.append(token)
                else:
                    command_token_set.append(token)
                detecting_token = token
                while detecting_token:
                    match = re.search(parenthesis_left, detecting_token.raw)
                    if match:
                        end = match.span()[-1]
                        detecting_token = detecting_token.split_from(end)
                        token_set_stack.append([detecting_token])
                    else:
                        detecting_token = None
                match = re.search(parenthesis_right, token.raw)
                if match:
                    right_parenthesis_num = len(match.group().split(')')) - 1
                    for idx in range(right_parenthesis_num):
                        pos_to_right = len(match.group().split(')', idx + 1)[-1]) + 1
                        try:
                            token_set = token_set_stack.pop()
                            token_set[-1] = token_set[-1].split_to(pos_to_right)
                            yield token_set
                        except IndexError:
                            raise ScriptParseException('No matching LeftParenthesis Found', token.lineno, line,
                                                       token.end_col_pos - pos_to_right)
            if token_set_stack:
                token = token_set_stack[-1][0]
                raise ScriptParseException('No matching RightParenthesis Found', token.lineno, line, token.col_pos)
            yield command_token_set
        command_parts = []


def iter_az_commands(script: str):
    for token_set in extract_token_sets_from_script(script):
        if token_set[0].content == 'az':
            yield token_set
