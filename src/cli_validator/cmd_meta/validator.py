from typing import List

from cli_validator.cmd_meta.loader import load_metas, build_command_tree
from cli_validator.cmd_meta.parser import CLIParser
from cli_validator.cmd_meta.util import support_ids
from cli_validator.cmd_tree import parse_command
from cli_validator.exceptions import ValidateHelpException, ParserHelpException, ConfirmationNoYesException, \
    ValidateFailureException, MissingSubCommandException, AmbiguousOptionException


class CommandMetaValidator(object):
    """A validator using Command Metadata generated from breaking change tool"""

    GLOBAL_PARAMETERS = [CLIParser.VERBOSE_FLAG, CLIParser.DEBUG_FLAG, CLIParser.ONLY_SHOW_ERRORS_FLAG,
                         '--output', '-o', '--query']

    def __init__(self, cache_dir: str = './cmd_meta'):
        """
        :param cache_dir: cache directory that store the downloaded metadata
        """
        self.cache_dir = cache_dir
        self.metas = None
        self.command_tree = None

    def load_metas(self, version: str):
        """
        :param version: the version of `azure-cli` that provides the metadata
        """
        self.metas = load_metas(version, self.cache_dir)
        self.command_tree = build_command_tree(self.metas)

    async def load_metas_async(self, version: str):
        from cli_validator.cmd_meta.loader.aio import load_metas
        self.metas = await load_metas(version, self.cache_dir)
        self.command_tree = build_command_tree(self.metas)

    def validate_command(self, command, non_interactive=False, placeholder=True, no_help=True, comments=True):
        """
        Validate a command to check if the command is valid
        :param command: command to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder:
        :param no_help: reject commands with `--help`
        :param comments: whether parse comments in the given command
        :return: parsed namespace
        """
        cmd = parse_command(self.command_tree, command, comments)
        if cmd.module is None:
            if no_help:
                raise ValidateHelpException()
            else:
                return
        meta = self.load_command_meta(cmd.signature, cmd.module)
        parser = self.build_parser(meta, placeholder)
        try:
            namespace = parser.parse_args(cmd.parameters)
        except ParserHelpException as e:
            if no_help:
                raise ValidateHelpException() from e
            else:
                return

        missing_args = []
        for param in meta['parameters']:
            if 'ids' in namespace and 'id_part' in param:
                continue
            if param.get('required', False) and namespace.__getattribute__(param['name']) is None:
                missing_args.append('/'.join(param['options']))
        if len(missing_args) > 0:
            raise ValidateFailureException(f"the following arguments are required: {', '.join(missing_args)} ")

        if meta.get('confirmation', False) and non_interactive and not ('yes' in namespace and namespace.yes):
            raise ConfirmationNoYesException()

    def validate_separate_command(self, command_signature: str, parameters: List[str], non_interactive=False, no_help=True):
        def handle_help():
            if no_help:
                raise ValidateHelpException()

        try:
            cmd = parse_command(self.command_tree, command_signature)
            if cmd.module is None:
                return handle_help()
        except MissingSubCommandException as e:
            if len(parameters) == 1 and parameters[0] in ['-h', '--help']:
                return handle_help()
            else:
                raise e
        meta = self.load_command_meta(cmd.signature, cmd.module)
        unresolved = []
        option_map = self._build_option_map(meta['parameters'])
        required = self._get_required_options(meta['parameters'])
        for param in parameters:
            param_meta = self._find_meta(option_map, param)
            if param_meta:
                if param_meta.get('required', False) and param_meta['name'] in required:
                    required.pop(param_meta['name'])
            elif param == '--ids' and support_ids(meta):
                for param_name in [param['name'] for param in meta['parameters'] if param.get('id_part')]:
                    if param_name in required:
                        required.pop(param_name)
            elif param in ['--help', '-h']:
                return handle_help()
            elif param in self.GLOBAL_PARAMETERS:
                continue
            else:
                unresolved.append(param)
        if len(unresolved) > 0:
            raise ValidateFailureException('unrecognized arguments: {}'.format(', '.join(unresolved)))
        if len(required) > 0:
            raise ValidateFailureException(
                'the following arguments are required: {}'.format(
                    ', '.join(['/'.join(param['options']) for param in required.values()])))

        if meta.get('confirmation', False) and non_interactive and not ('--yes' in parameters or '-y' in parameters):
            raise ConfirmationNoYesException()

    @staticmethod
    def _build_option_map(params):
        param_metas = {}
        for param in params:
            for name in param['options']:
                param_metas[name] = param
                for n in range(2, len(name)):
                    partial = name[:n]
                    if partial != '--':
                        if partial not in param_metas:
                            param_metas[partial] = []
                        if isinstance(param_metas[partial], list):
                            param_metas[partial].append(param)
        return param_metas

    @staticmethod
    def _get_required_options(params):
        required = {}
        for param in params:
            if param.get('required', False):
                required[param['name']] = param
        return required

    @staticmethod
    def _find_meta(option_map, user_param):
        if user_param in option_map:
            param_meta = option_map[user_param]
            if isinstance(param_meta, list):
                if len(param_meta) >= 2:
                    options = []
                    for meta in param_meta:
                        for option in meta['options']:
                            options.append(option)
                    raise AmbiguousOptionException(user_param, options)
                elif len(param_meta) == 1:
                    return param_meta[0]
            elif isinstance(param_meta, dict):
                return param_meta
        return None

    def load_command_meta(self, signature, module):
        """
        Load metadata of specific command.
        :param signature: command signature
        :param module:
        :return:
        """
        module_meta = self.metas[f'az_{module}_meta.json']
        meta = module_meta
        for idx in range(len(signature) - 1):
            meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
        return meta['commands'][' '.join(signature)]

    @staticmethod
    def build_parser(meta, placeholder=True):
        parser = CLIParser(add_help=True)
        parser.load_meta(meta, placeholder=placeholder)
        return parser
