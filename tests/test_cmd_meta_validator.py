from unittest import TestCase
from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateFailureException


class TestCmdChangeValidator(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.validator = CommandMetaValidator('2.50.0', 'test_meta')

    # Test cases
    def test_validate_correct_command_with_no_ids(self):
        self.validator.validate_command('az storage account show -g qinkai-test -n storageqinkai')
        
    def test_validate_correct_command_with_ids(self):
        self.validator.validate_command('az storage account show --ids /subscriptions/0b1f6471-1bf0-4dda-aec3-cb9272f09590/resourceGroups/qinkai-test/providers/Microsoft.Storage/storageAccounts/storageqinkai')
    
    def test_validate_correct_command_with_ids_and_separated_parameter_with_id_part(self):
        self.validator.validate_command('az storage account show --ids /subscriptions/0b1f6471-1bf0-4dda-aec3-cb9272f09590/resourceGroups/qinkai-test/providers/Microsoft.Storage/storageAccounts/storageqinkai -n storageqin')
    
    def test_validate_correct_command_with_ids_and_required_parameter(self):
        self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx -p plan-test')
    
    def test_validate_incorrect_command_with_required_parameters_needed(self):
        self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')
    
    def test_validate_command_without_required_parameters(self):
        self.validator.validate_command('az sig list-community --location myLocation')
