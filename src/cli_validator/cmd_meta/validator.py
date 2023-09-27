import shlex
from typing import List, Optional

from cli_validator.cmd_meta.loader import load_metas, build_command_tree
from cli_validator.cmd_meta.parser import CLIParser
from cli_validator.cmd_meta.util import support_ids
from cli_validator.cmd_tree import CommandTreeParser
from cli_validator.exceptions import ValidateHelpException, ParserHelpException, ConfirmationNoYesException, \
    ValidateFailureException, MissingSubCommandException, AmbiguousOptionException, TooLongSignatureException


class CommandMetaValidator(object):
    """A validator using Command Metadata generated from breaking change tool"""

    GLOBAL_PARAMETERS = [CLIParser.VERBOSE_FLAG, CLIParser.DEBUG_FLAG, CLIParser.ONLY_SHOW_ERRORS_FLAG,
                         '--output', '-o', '--query']
    GLOBAL_PARAMETERS_META = [{
        "name": "VERBOSE_FLAG",
        "options": [CLIParser.VERBOSE_FLAG]
    }, {
        "name": "DEBUG_FLAG",
        "options": [CLIParser.DEBUG_FLAG]
    }, {
        "name": "ONLY_SHOW_ERRORS_FLAG",
        "options": [CLIParser.ONLY_SHOW_ERRORS_FLAG],
    }, {
        "name": CLIParser.OUTPUT_DEST,
        "options": ["--output", "-o"]
    }, {
        "name": "_jmespath_query",
        "options": ["--query"]
    }]

    def __init__(self, cache_dir: str = './cmd_meta'):
        """
        :param cache_dir: cache directory that store the downloaded metadata
        """
        self.cache_dir = cache_dir
        self.metas = None
        self.command_tree: Optional[CommandTreeParser] = None

    def load_metas(self, version: str, force_refresh=False):
        """
        :param version: the version of `azure-cli` that provides the metadata
        :param force_refresh: load the metadata through network no matter whether there is a cache
        """
        self.metas = load_metas(version, self.cache_dir, force_refresh=force_refresh)
        self.command_tree = build_command_tree(self.metas)

    async def load_metas_async(self, version: str, force_refresh=False):
        from cli_validator.cmd_meta.loader.aio import load_metas
        self.metas = await load_metas(version, self.cache_dir, force_refresh=force_refresh)
        self.command_tree = build_command_tree(self.metas)

    def validate_command(self, command: List[str], non_interactive=False, placeholder=True, no_help=True):
        """
        Validate a command to check if the command is valid
        :param command: command to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder: allow placeholder like <ResourceName>, $ResourceName as field value
        :param no_help: reject commands with `--help`
        :return: parsed namespace
        """
        def handle_help(e=None):
            if no_help:
                raise ValidateHelpException() from e

        cmd = self.command_tree.parse_command(command)
        if cmd.module is None:
            return handle_help()
        meta = self.load_command_meta(cmd.signature, cmd.module)
        parser = self.build_parser(meta, placeholder)
        try:
            namespace = parser.parse_args(cmd.parameters)
        except ParserHelpException as e:
            return handle_help(e)

        missing_args = []
        for param in meta['parameters']:
            if 'ids' in namespace and 'id_part' in param:
                continue
            if param.get('required', False) and namespace.__getattribute__(param['name']) is None:
                missing_args.append('/'.join(param['options']) if param['options'] else f'<{param["name"].upper()}>')
        if len(missing_args) > 0:
            raise ValidateFailureException(f"the following arguments are required: {', '.join(missing_args)} ")

        if meta.get('confirmation', False) and non_interactive and not ('yes' in namespace and namespace.yes):
            raise ConfirmationNoYesException()

    def validate_sig_params(self, signature: List[str], parameters: List[str], non_interactive=False, no_help=True):
        def handle_help(e=None):
            if no_help:
                raise ValidateHelpException() from e

        try:
            cmd = self.command_tree.parse_command(signature)
            if cmd.module is None:
                return handle_help()
        except MissingSubCommandException as e:
            if len(parameters) == 1 and parameters[0] in ['-h', '--help']:
                return handle_help(e)
            else:
                raise e
        if cmd.parameters:
            raise TooLongSignatureException(shlex.join(signature), 'az ' + shlex.join(cmd.signature))
        meta = self.load_command_meta(cmd.signature, cmd.module)
        unresolved = []
        param_metas = meta['parameters'] + self.GLOBAL_PARAMETERS_META
        if 'subscription' not in [p['name'] for p in meta['parameters']]:
            param_metas.append({"name": "_subscription", "options": ['--subscription']})
        option_map = self._build_option_map(param_metas)
        required = self._get_required_options(param_metas)
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
                            if option.startswith(user_param):
                                options.append(option)
                    raise AmbiguousOptionException(user_param, options)
                elif len(param_meta) == 1:
                    return param_meta[0]
            elif isinstance(param_meta, dict):
                return param_meta
        return None

    def load_command_meta(self, signature: List[str], module: str):
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
