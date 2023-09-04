from cli_validator.cmd_meta.loader import load_metas, build_command_tree
from cli_validator.cmd_meta.parser import CLIParser
from cli_validator.cmd_tree import parse_command
from cli_validator.exceptions import ValidateHelpException, ParserHelpException, ConfirmationNoYesException


class CommandMetaValidator(object):
    """A validator using Command Metadata generated from breaking change tool"""
    def __init__(self, version: str, cache_dir: str = './cmd_meta'):
        """
        :param version: the version of `azure-cli` that provides the metadata
        :param cache_dir: cache directory that store the downloaded metadata
        """
        self.metas = load_metas(version, cache_dir)
        self.command_tree = build_command_tree(self.metas)
        self._global_parser = CLIParser.create_global_parser()

    def validate_command(self, command, non_interactive=False, no_help=True, comments=True):
        """
        Validate a command to check if the command is valid
        :param command: command to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param no_help: reject commands with `--help`
        :param comments: whether parse comments in the given command
        :return: parsed namespace
        """
        cmd = parse_command(self.command_tree, command, comments)
        # At present, only az command group --help will return a CommandInfo with module as None
        if cmd.module is None:
            if no_help:
                raise ValidateHelpException()
            else:
                return
        meta = self.load_command_meta(cmd.signature, cmd.module)
        parser = self.build_parser(meta)
        try:
            namespace = parser.parse_args(cmd.parameters)
        except ParserHelpException as e:
            if no_help:
                raise ValidateHelpException() from e
            else:
                return
        if 'confirmation' in meta and meta['confirmation']:
            if non_interactive and not ('yes' in namespace and namespace.yes):
                raise ConfirmationNoYesException()

    def load_command_meta(self, signature, module):
        """
        Load metadata of specific command.
        :param signature: command signature
        :param module:
        :return:
        """
        module_meta = self.metas[f'az_{module}_meta.json']
        meta = module_meta
        for idx in range(len(signature)-1):
            meta = meta['sub_groups'][' '.join(signature[:idx+1])]
        return meta['commands'][' '.join(signature)]

    def build_parser(self, meta):
        parser = CLIParser(parents=[self._global_parser], add_help=True)
        parser.load_meta(meta)
        return parser
