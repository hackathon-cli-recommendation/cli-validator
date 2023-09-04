from unittest import TestCase
from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException, ValidateFailureException


class TestCmdChangeValidator(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.validator = CommandMetaValidator('2.50.0', 'test_meta')

    def test_validate_command(self):
        self.validator.validate_command('az webapp create -g g -n n -p p')
        self.validator.validate_command('az vm create -n n --resource-group g')
        with self.assertRaises(ValidateFailureException):
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

    def test_validate_correct_command_with_no_ids(self):
        self.validator.validate_command('az storage account show -g xxxxx -n xxxxx')
        
    def test_validate_correct_command_with_ids(self):
        self.validator.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx')

    def test_validate_correct_command_with_ids_and_separated_parameter_with_id_part(self):
        self.validator.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx -n xxxxx')
    
    def test_validate_correct_command_with_ids_and_required_parameter(self):
        self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx -p xxxxx')
    
    def test_validate_incorrect_command_with_required_parameters_needed(self):
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')
    
    def test_validate_command_without_required_parameters(self):
        self.validator.validate_command('az sig list-community --location xxxxx')
