from unittest import TestCase

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException


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
