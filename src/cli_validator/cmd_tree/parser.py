import shlex
from typing import List, Optional

from cli_validator.cmd_tree.loader import load_command_tree
from cli_validator.command import CommandInfo
from cli_validator.exceptions import EmptyCommandException, NonAzCommandException, CommandTreeCorruptedException, \
    UnknownCommandException, MissingSubCommandException


class CommandTreeParser(object):
    def __init__(self, cmd_tree: Optional[dict] = None):
        self.cmd_tree = cmd_tree

    @staticmethod
    def load(url: str, file_path: str):
        return CommandTreeParser(load_command_tree(url, file_path))

    def parse_command(self, command: List[str]):
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
                    raise CommandTreeCorruptedException('Core')
            elif parameters[0] in ['--help', '-h'] and len(parameters) == 1:
                return CommandInfo(None, signature, parameters)
            else:
                raise UnknownCommandException(shlex.join(command))
        raise MissingSubCommandException(shlex.join(command))
