from typing import List


class VersionNotExistException(Exception):
    def __init__(self, version: str, product: str):
        self.msg = f'Metadata of {product} {version} not Found'


class ValidateFailureException(Exception):
    def __init__(self, msg):
        self.msg = msg


class CommandMetaNotFoundException(ValidateFailureException):
    def __init__(self, sig: List[str]):
        super().__init__('Command Metadata of "az {}" is not Found'.format(' '.join(sig)))


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
        super().__init__(f'Unknown Command: "{command}".')


class MissingSubCommandException(UnknownCommandException):
    def __init__(self, command):
        super().__init__(command)


class TooLongSignatureException(UnknownCommandException):
    def __init__(self, command, fixed):
        super().__init__(command)
        self.msg += f' Do you mean "{fixed}"?'


class ScriptParseException(ValidateFailureException):
    def __init__(self, msg: str, lineno: int, line: str, col_pos: int):
        super().__init__(f'Fail to parse script: {msg} in Line {lineno}, Col {col_pos}: \n{line}')
