import argparse
import re
from typing import NoReturn

from cli_validator.cmd_meta.util import support_ids
from cli_validator.exceptions import ParserHelpException, ParserFailureException, ChoiceNotExistsException


class CustomHelpAction(argparse.Action):
    """
    The new help action to overwrite the origin help implementation.\n
    Now the help will raise an Exception to avoid the check of required arguments.
    """

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise ParserHelpException()


class CLIParser(argparse.ArgumentParser):
    DEBUG_FLAG = '--debug'
    VERBOSE_FLAG = '--verbose'
    ONLY_SHOW_ERRORS_FLAG = '--only-show-errors'

    OUTPUT_DEST = '_output_format'

    _OUTPUT_FORMAT_DICT = {
        'json',
        'jsonc',
        'yaml',
        'yamlc',
        'table',
        'tsv',
        'none',
    }
    TYPE_MAP = {
        'String': str,
        'str': str,
        'List<String>': str,
        'Boolean': bool,
        'bool': bool,
        'List<Boolean>': bool,
        'Int': int,
        'int': int,
        'List<Int>': int,
        'Float': float,
        'float': float,
        'List<Float>': float,
        'custom_type': str,
        'file_type': str,
        'Object': str,
        'Dict<String,String>': str,
        'List<Object>': str,
        'Dict<String,Object>': str,
        'Dict<String,List<String>>': str,
        'Duration': int,
        'Date': str,
        'Time': str,
        'DateTime': str,
        'Password': str,
        'GUID/UUID': str,
    }

    PLACEHOLDER_REGEX = (r'(\$[a-zA-Z0-9_]*$)|'
                         r'(\$\{[a-zA-Z0-9_ -\.\[\]]*\}$)|'
                         r'(\$\([a-zA-Z0-9_ -\.\[\]]*\)$)|'
                         r'(\<[a-zA-Z0-9_ ]*\>$)|'
                         r'(\<\<[a-zA-Z0-9_ -]*\>\>$)')

    @classmethod
    def placeholder_type(cls, options, back_type, choices=None):
        def type_convert(raw_query):
            if re.match(cls.PLACEHOLDER_REGEX, raw_query):
                return raw_query
            else:
                value = back_type(raw_query)
                if choices and value not in choices:
                    raise ChoiceNotExistsException(options, value, choices)
                return value
        # Display the correct type name in error message
        setattr(type_convert, '__name__', back_type.__name__)
        return type_convert

    @staticmethod
    def jmespath_type(raw_query):
        """Compile the query with JMESPath and return the compiled result.
        JMESPath raises exceptions which subclass from ValueError.
        In addition, though, JMESPath can raise a KeyError.
        ValueErrors are caught by argparse so argument errors can be generated.
        """
        from jmespath import compile as compile_jmespath
        try:
            return compile_jmespath(raw_query)
        except KeyError as ex:
            # Raise a ValueError which argparse can handle
            raise ValueError from ex

    def __init__(self, **kwargs):
        self.subparsers = {}
        self.parents = kwargs.get('parents', [])
        # Overwrite the old help implement
        add_help = kwargs.get('add_help', True)
        kwargs['add_help'] = False
        super().__init__(**kwargs)
        self.register('action', 'help', CustomHelpAction)
        if add_help:
            self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS)

    def load_meta(self, meta, placeholder=True, check_required=False):
        """
        Load metadata of a module
        :param placeholder: allow placeholder like <ResourceName>, $ResourceName as field value
        :param check_required: load the `required` field into the parser
        :param meta: loaded metadata dict
        """
        for param in meta['parameters']:
            kwargs = {
                'dest': param.get('name'),
                'default': param.get('default'),
            }
            if 'choices' in param and not placeholder:
                kwargs['choices'] = param['choices']
            kwargs['nargs'] = param.get('nargs', '?')
            if 'type' in param:
                if placeholder:
                    kwargs['type'] = self.placeholder_type(param['options'], self.TYPE_MAP.get(param['type'], str))
                else:
                    kwargs['type'] = self.TYPE_MAP.get(param['type'], str)
            if check_required and 'required' in param and len(param['options']) > 0:
                kwargs['required'] = param['required']
            if param['name'] == 'yes':
                kwargs['action'] = 'store_true'
                kwargs.pop('nargs')
            self.add_argument(*param['options'], **kwargs)
        self._add_global(placeholder, 'subscription' not in [p['name'] for p in meta['parameters']])
        if support_ids(meta) and 'ids' not in [param['name'] for param in meta['parameters']]:
            self.add_argument('--ids', dest='ids', nargs='+')

    def _add_global(self, placeholder=True, subscription=True):
        """
        Create a global Argument Parser for Global Arguments. This should be the parent of all subcommands.
        """
        arg_group = self.add_argument_group('global', 'Global Arguments')
        arg_group.add_argument(CLIParser.VERBOSE_FLAG, dest='_log_verbosity_verbose', action='store_true',
                               help='Increase logging verbosity. Use --debug for full debug logs.')
        arg_group.add_argument(CLIParser.DEBUG_FLAG, dest='_log_verbosity_debug', action='store_true',
                               help='Increase logging verbosity to show all debug logs.')
        arg_group.add_argument(CLIParser.ONLY_SHOW_ERRORS_FLAG, dest='_log_verbosity_only_show_errors',
                               action='store_true',
                               help='Only show errors, suppressing warnings.')
        arg_group.add_argument('--output', '-o', dest=CLIParser.OUTPUT_DEST,
                               choices=list(CLIParser._OUTPUT_FORMAT_DICT) if not placeholder else None,
                               default='json',
                               help='Output format',
                               type=self.placeholder_type(['--query'], str.lower, choices=list(CLIParser._OUTPUT_FORMAT_DICT)))
        arg_group.add_argument('--query', dest='_jmespath_query', metavar='JMESPATH',
                               help='JMESPath query string. See http://jmespath.org/ for more'
                                    ' information and examples.',
                               type=self.placeholder_type(['--query'], CLIParser.jmespath_type))
        if subscription:
            self.add_argument('--subscription', dest='_subscription')

    def error(self, message: str) -> NoReturn:
        """
        Raise an exception when parse fails.
        :param message: error message
        """
        raise ParserFailureException(message)
