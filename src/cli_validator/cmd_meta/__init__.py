import shlex

from cli_validator.result import Result
from cli_validator.cmd_meta.loader import load_metas
from cli_validator.cmd_meta.parser import CLIParser, ParserHelpException, ParserFailureException


class CommandValidatorWithMeta(object):
    """A validator using Command Metadata generated from breaking change tool"""
    def __init__(self, version: str, cache_dir: str = './cmd_meta'):
        """
        :param version: the version of `azure-cli` that provides the metadata
        :param cache_dir: cache directory that store the downloaded metadata
        """
        self.metas = load_metas(version, cache_dir)
        self._global_parser = CLIParser.create_global_parser()
        self.parser = CLIParser(prog='az', parents=[self._global_parser])
        self.parser.add_subcmd_help()
        for meta in self.metas.values():
            self.parser.load_meta(meta)

    def validate_command(self, command: str, comments=True):
        """
        Validate a command to check if the command is valid
        :param command: command to be validated
        :param comments: whether parse comments in the given command
        :return: a Result tell whether the command is valid
        """
        args = shlex.split(command, comments)
        if len(args) == 0:
            return Result(False, 'Empty Command')
        elif args[0] != 'az':
            return Result(False, 'Not az Command')
        else:
            try:
                self.parser.parse_args(args[1:])
            except ParserHelpException:
                # The command contains `--help` and shouldn't check whether other arguments is required
                return Result(True)
            except ParserFailureException as e:
                return Result(False, e.msg)
            else:
                return Result(True)
