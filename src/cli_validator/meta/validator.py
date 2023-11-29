import re
from typing import List

from cli_validator.meta.parser import CLIParser
from cli_validator.meta.util import support_ids
from cli_validator.exceptions import ValidateHelpException, ParserHelpException, ConfirmationNoYesException, \
    ValidateFailureException, AmbiguousOptionException


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

    def __init__(self, meta: dict):
        """
        :param meta: cache directory that store the downloaded metadata
        """
        self.meta = meta

    def validate_params(self, parameters: List[str], non_interactive=False, placeholder=True, no_help=True):
        """
        Validate a command to check if the command is valid
        :param parameters: parameters in command to be validated
        :param non_interactive: check `--yes` in a command with confirmation
        :param placeholder: allow placeholder like <ResourceName>, $ResourceName as field value
        :param no_help: reject commands with `--help`
        :return: parsed namespace
        """

        def handle_help(e=None):
            if no_help:
                raise ValidateHelpException() from e
            return None

        parser = self.build_parser(self.meta, placeholder)
        try:
            namespace = parser.parse_args(parameters)
        except ParserHelpException as e:
            return handle_help(e)

        missing_args = []
        for param in self.meta['parameters']:
            if 'ids' in namespace and namespace.ids and 'id_part' in param:
                continue
            if param.get('required', False) and namespace.__getattribute__(param['name']) is None:
                missing_args.append('/'.join(param['options']) if param['options'] else f'<{param["name"].upper()}>')
        if len(missing_args) > 0:
            raise ValidateFailureException(f"the following arguments are required: {', '.join(missing_args)} ")

        if self.meta.get('confirmation', False) and non_interactive and not ('yes' in namespace and namespace.yes):
            raise ConfirmationNoYesException()

    def validate_param_keys(self, parameters: List[str], non_interactive=False, no_help=True):
        def handle_help(e=None):
            if no_help:
                raise ValidateHelpException() from e
            return None

        unresolved = []
        param_metas = self.meta['parameters'] + self.GLOBAL_PARAMETERS_META
        if 'subscription' not in [p['name'] for p in self.meta['parameters']]:
            param_metas.append({"name": "_subscription", "options": ['--subscription']})
        option_map = self._build_option_map(param_metas)
        positional_metas = [meta for meta in param_metas if len(meta["options"]) == 0]
        required = self._get_required_options(param_metas)
        for param in parameters:
            param_meta = self._find_meta(option_map, param)
            if param_meta:
                if param_meta.get('required', False) and param_meta['name'] in required:
                    required.pop(param_meta['name'])
            elif param == '--ids' and support_ids(self.meta):
                for param_name in [param['name'] for param in self.meta['parameters'] if param.get('id_part')]:
                    if param_name in required:
                        required.pop(param_name)
            elif param in ['--help', '-h']:
                return handle_help()
            elif re.match(r'<[a-zA-Z-_.|]+>', param):
                if len(positional_metas) == 1 and positional_metas[0]['name'] in required:
                    required.pop(positional_metas[0]['name'])
                elif param[1:-1].lower() in required and len(required[param[1:-1].lower()]["options"]) == 0:
                    required.pop(param[1:-1].lower())
            else:
                unresolved.append(param)
        if len(unresolved) > 0:
            raise ValidateFailureException('unrecognized arguments: {}'.format(', '.join(unresolved)))
        if len(required) > 0:
            raise ValidateFailureException(
                'the following arguments are required: {}'.format(
                    ', '.join(['/'.join(param['options']) if param['options'] else f'<{param["name"].upper()}>'
                               for param in required.values()])))

        if self.meta.get('confirmation', False) and non_interactive \
                and not ('--yes' in parameters or '-y' in parameters):
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

    @staticmethod
    def build_parser(meta, placeholder=True):
        parser = CLIParser(add_help=True)
        parser.load_meta(meta, placeholder=placeholder)
        return parser
