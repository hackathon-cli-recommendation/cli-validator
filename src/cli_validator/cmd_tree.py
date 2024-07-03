import shlex
from enum import Enum
from typing import List, Optional

from cli_validator.exceptions import EmptyCommandException, NonAzCommandException, CommandTreeCorruptedException, \
    UnknownCommandException, MissingSubCommandException


class CommandSource(str, Enum):
    UNKNOWN = "Unknown Source"
    CORE_MODULE = "Core Module"
    EXTENSION = "Extension"


class CommandInfo(object):
    def __init__(self, module: Optional[str], signature: List[str], parameters: List[str]):
        self.module = module
        self.signature = signature
        self.parameters = parameters


class CommandTreeParser(object):
    def __init__(self, cmd_tree: dict, source: CommandSource):
        self.cmd_tree = cmd_tree
        self.source = source

    def parse_command(self, command: List[str]) -> CommandInfo:
        """
        Parse a Command into CommandInfo using CommandTree
        :param command: command to be validated
        :return: parsed `CommandInfo`. The `module` of `CommandInfo` is `None` if the command is a help command.
        """
        if len(command) == 0:
            raise EmptyCommandException()
        elif command[0] != 'az':
            raise NonAzCommandException()
        elif command[1] == 'help' and len(command) == 2:
            return CommandInfo(None, [command[1]], [])
        parameters = command[1:]
        signature = []
        # Go through the node in the tree that matches each word in the signature
        cur_node = self.cmd_tree
        for part in command[1:]:
            if part in cur_node:
                signature.append(part)
                parameters.pop(0)
                if isinstance(cur_node[part], str):
                    # The module of the command is stored in the leaf node
                    return CommandInfo(cur_node[part], signature, parameters)
                elif isinstance(cur_node[part], dict):
                    cur_node = cur_node[part]
                else:
                    raise CommandTreeCorruptedException(self.source)
            elif parameters[0] in ['--help', '-h'] and len(parameters) == 1:
                return CommandInfo(None, signature, parameters)
            else:
                raise UnknownCommandException(shlex.join(command))
        raise MissingSubCommandException(shlex.join(command))
