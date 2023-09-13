import unittest

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException, ValidateFailureException


class TestCmdChangeValidator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.validator = CommandMetaValidator('test_meta')
        await self.validator.load_metas_async('2.50.0')

    async def test_validate_command(self):
        self.validator.validate_command('az webapp create -g g -n n -p p')
        self.validator.validate_command('az vm create -n n --resource-group g')
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_command('az vm create -n n')
        with self.assertRaises(ParserFailureException):
            self.validator.validate_command('az vm create -n n -g g --unknown')
        self.validator.validate_separate_command('az webapp create', ['-g', '-n', '-p'])
        self.validator.validate_separate_command('az vm create', ['-n', '--resource-group'])
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_separate_command('az vm create', ['-n'])
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_separate_command('az vm create', ['-n', '-g', '--unknown'])

    def test_help(self):
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az help')
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az webapp --help')
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_command('az webapp unknown --help')
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_command('az webapp create --help')
        self.validator.validate_command('az help', no_help=False)
        self.validator.validate_command('az webapp --help', no_help=False)
        self.validator.validate_command('az webapp create --help', no_help=False)
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_separate_command('az help', [])
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_separate_command('az webapp', ['--help'])
        with self.assertRaises(ValidateHelpException):
            self.validator.validate_separate_command('az webapp create', ['--help'])
        self.validator.validate_separate_command('az help', [], no_help=False)
        self.validator.validate_separate_command('az webapp', ['--help'], no_help=False)
        self.validator.validate_separate_command('az webapp create', ['--help'], no_help=False)

    def test_confirmation(self):
        self.validator.validate_command('az group delete -n n')
        self.validator.validate_command('az group delete -n n -y')
        with self.assertRaises(ConfirmationNoYesException):
            self.validator.validate_command('az group delete -n n', non_interactive=True)
        self.validator.validate_command('az group delete -n n -y', non_interactive=True)
        self.validator.validate_command('az group delete -n n --yes', non_interactive=True)
        self.validator.validate_separate_command('az group delete', ['-n'])
        self.validator.validate_separate_command('az group delete', ['-n', '-y'])
        with self.assertRaises(ConfirmationNoYesException):
            self.validator.validate_separate_command('az group delete', ['-n'], non_interactive=True)
        self.validator.validate_separate_command('az group delete', ['-n', '-y'], non_interactive=True)
        self.validator.validate_separate_command('az group delete', ['-n', '--yes'], non_interactive=True)

    def test_shorthand_syntax(self):
        self.validator.validate_command('az network route-table create -g g -n n --tag "{a:b,c:d}" --tag e=f')

    def test_placeholder(self):
        self.validator.validate_command('az network public-ip create -g g -n n --sku Standard')
        self.validator.validate_command('az network public-ip create -g $rgName -n ${name} --sku <SKU_NAME>')
        
    def test_validate_command_with_ids(self):
        self.validator.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx')
        self.validator.validate_separate_command('az storage account show', ['--ids'])
        self.validator.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx -n xxxxx')
        self.validator.validate_separate_command('az storage account show', ['--ids', '-n'])
        with self.assertRaisesRegex(ParserFailureException, r'unrecognized arguments: --ids .*'):
            self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx -p xxxxx')
        with self.assertRaisesRegex(ValidateFailureException, r'unrecognized arguments: --ids.*'):
            self.validator.validate_separate_command('az webapp create', ['--ids', '-p'])
        with self.assertRaises(ValidateFailureException):
            self.validator.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')

    def test_global_parameter(self):
        self.validator.validate_command('az group show -n qinkai-test -o tsv')
        self.validator.validate_separate_command('az group show', ['-n', '-o'])
