from unittest import TestCase

from cli_validator.cmd_meta import CommandValidatorWithMeta


class TestCmdChangeValidator(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.validator = CommandValidatorWithMeta('2.50.0', 'test_meta')

    def test_validate_command(self):
        self.assertTrue(self.validator.validate_command('az webapp create -g g -n n -p p').no_error)
        self.assertTrue(self.validator.validate_command('az vm create -n n --resource-group g').no_error)
        self.assertFalse(self.validator.validate_command('az vm create -n n').no_error)
        self.assertFalse(self.validator.validate_command('az vm create -n n -g g --unknown').no_error)
