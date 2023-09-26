class UnknownTypeException(Exception):
    def __init__(self, typ):
        self.msg = f'Unknown Type: {typ}.'


class ValidateFailureException(Exception):
    def __init__(self, msg):
        self.msg = msg


class ParserFailureException(ValidateFailureException):
    def __init__(self, msg):
        super().__init__(msg)


class ValidateHelpException(ValidateFailureException):

    def __init__(self):
        super().__init__('The input command is help or `--help`.')


class ParserHelpException(ValidateFailureException):
    def __init__(self):
        super().__init__('The user inputs `-h/--help`. This is not a real exception.')


class ChoiceNotExistsException(ValidateFailureException):

    def __init__(self, argument, param, choices):
        super().__init__("argument {}: invalid choice: '{}' (choose from {})".format(
            "/".join(argument), param, ', '.join([f"'{c}'" for c in choices])))


class AmbiguousOptionException(ValidateFailureException):

    def __init__(self, input_arg, matches):
        super().__init__("ambiguous option: {} could match {}".format(input_arg, ", ".join(matches)))


class ConfirmationNoYesException(ValidateFailureException):

    def __init__(self):
        super().__init__('`--yes` is required for commands in non-interactive mode.')


class EmptyCommandException(ValidateFailureException):
    def __init__(self):
        super().__init__('The input command is empty.')


class NonAzCommandException(ValidateFailureException):
    def __init__(self):
        super().__init__('The input command is not an Azure CLI command.')


class CommandTreeCorruptedException(ValidateFailureException):
    def __init__(self, tree_type):
        super().__init__(f'The {tree_type} CommandTree is Corrupted. Fail to find parent module/extension of command.')


class UnknownCommandException(ValidateFailureException):
    def __init__(self, command):
        super().__init__(f'Unknown Command: \'{command}\'.')


class MissingSubCommandException(UnknownCommandException):
    def __init__(self, command):
        super().__init__(command)


class TooLongSignatureException(UnknownCommandException):
    def __init__(self, command, fixed):
        super().__init__(command)
        self.msg += f' Do you mean \'{fixed}\'?'
