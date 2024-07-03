from typing import List


class ValidatorException(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg


class MetadataException(ValidatorException):
    def __init__(self, msg: str):
        super().__init__(msg)


class CommandTreeRetrieveException(MetadataException):
    def __init__(self, source):
        self.msg = f'Fail to retrieve command tree of {source}'


class MetadataRetrieveException(MetadataException):
    def __init__(self):
        self.msg = f'Fail to retrieve metadata'


class VersionListRetrieveException(MetadataException):
    def __init__(self):
        self.msg = f'Fail to retrieve version list'


class EmptyVersionListException(MetadataException):
    def __init__(self):
        self.msg = f'Retrieved Version List is Empty'


class CommandTreeException(ValidatorException):
    def __init__(self, msg: str):
        super().__init__(msg)


class EmptyCommandException(CommandTreeException):
    def __init__(self):
        super().__init__('The input command is empty.')


class NonAzCommandException(CommandTreeException):
    def __init__(self):
        super().__init__('The input command is not an Azure CLI command.')


class CommandTreeCorruptedException(CommandTreeException):
    def __init__(self, tree_type):
        super().__init__(f'The {tree_type} CommandTree is Corrupted. Fail to find parent module/extension of command.')


class UnknownCommandException(CommandTreeException):
    def __init__(self, command):
        super().__init__(f'Unknown Command: "{command}".')


class MissingSubCommandException(UnknownCommandException):
    def __init__(self, command):
        super().__init__(command)


class TooLongSignatureException(UnknownCommandException):
    def __init__(self, command, fixed):
        super().__init__(command)
        self.msg += f' Do you mean "{fixed}"?'


class ValidateException(ValidatorException):
    def __init__(self, msg: str):
        super().__init__(msg)


class CommandMetaNotFoundException(ValidateException):
    def __init__(self, sig: List[str]):
        super().__init__('Command Metadata of "az {}" is not Found'.format(' '.join(sig)))


class ParserException(ValidateException):
    def __init__(self, msg: str):
        super().__init__(msg)


class ValidateHelpException(ValidateException):
    def __init__(self):
        super().__init__('The input command is help or `--help`.')


class ParserHelpException(ValidateException):
    def __init__(self):
        super().__init__('The user inputs `-h/--help`. This is not a real exception.')


class ChoiceNotExistsException(ValidateException):
    def __init__(self, argument, param, choices):
        super().__init__("argument {}: invalid choice: '{}' (choose from {})".format(
            "/".join(argument), param, ', '.join([f"'{c}'" for c in choices])))


class AmbiguousOptionException(ValidateException):
    def __init__(self, input_arg, matches):
        super().__init__("ambiguous option: {} could match {}".format(input_arg, ", ".join(matches)))


class ConfirmationNoYesException(ValidateException):
    def __init__(self):
        super().__init__('`--yes` is required for commands in non-interactive mode.')


class ScriptParseException(ValidatorException):
    def __init__(self, msg: str, lineno: int, line: str, col_pos: int):
        super().__init__('Fail to parse script: {msg} in Line {lineno}, Col {col_pos}: \n{line}')
