from unittest import TestCase

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException


class TestCmdChangeValidator(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.validator = CommandMetaValidator('2.50.0', 'test_meta')

    def test_validate_command(self):
        self.validator.validate_command('az webapp create -g g -n n -p p')
        self.validator.validate_command('az vm create -n n --resource-group g')
        with self.assertRaises(ParserFailureException):
            self.validator.validate_command('az vm create -n n')
        with self.assertRaises(ParserFailureException):
            self.validator.validate_command('az vm create -n n -g g --unknown')

    def test_help(self):
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az help')
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az webapp --help')
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az webapp create --help')
        self.validator.validate_command('az help', no_help=False)
        self.validator.validate_command('az webapp --help', no_help=False)
        self.validator.validate_command('az webapp create --help', no_help=False)

    def test_confirmation(self):
        self.validator.validate_command('az group delete -n n')
        self.validator.validate_command('az group delete -n n -y')
        with self.assertRaises(ConfirmationNoYesException):
            self.validator.validate_command('az group delete -n n', non_interactive=True)
        self.validator.validate_command('az group delete -n n -y', non_interactive=True)
        self.validator.validate_command('az group delete -n n --yes', non_interactive=True)
