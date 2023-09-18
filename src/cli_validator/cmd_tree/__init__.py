import shlex

from cli_validator import CommandInfo
from cli_validator.exceptions import EmptyCommandException, NonAzCommandException, CommandTreeCorruptedException, \
    UnknownCommandException, MissingSubCommandException


def parse_command(command_tree, command, comments=True):
    """
    Parse a Command into CommandInfo using CommandTree
    :param command_tree:
    :param command: command to be validated
    :return: parsed CommandInfo
    """
    args = shlex.split(command, comments)
    if len(args) == 0:
        raise EmptyCommandException()
    elif args[0] != 'az':
        raise NonAzCommandException()
    elif args[1] == 'help' and len(args) == 2:
        return CommandInfo(None, ['help'], [])
    parameters = args[1:]
    signature = []
    cur_node = command_tree
    for part in args[1:]:
        if part in cur_node:
            signature.append(part)
            parameters.pop(0)
            if isinstance(cur_node[part], str):
                return CommandInfo(cur_node[part], signature, parameters)
            elif isinstance(cur_node[part], dict):
                cur_node = cur_node[part]
            else:
                raise CommandTreeCorruptedException('Core')
        elif parameters[0] in ['--help', '-h'] and len(parameters) == 1:
            return CommandInfo(None, signature, parameters)
        else:
            raise UnknownCommandException(command)
    raise MissingSubCommandException(command)
