import unittest

from cli_validator import CommandInfo
from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException, \
    ValidateFailureException, AmbiguousOptionException, UnmatchedBracketsException


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
        self.validator.validate_command('az network public-ip create -g $rgName -n $name --sku <SKU_NAME>')
        
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

    def test_network(self):
        self.validator.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --address-prefix 10.0.0.0/8 --subnet-name chatgpt-Subnet-123456 --subnet-prefix 10.0.0.0/24')
        self.validator.validate_separate_command('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--subnet-name', '--subnet-prefix'])

    def test_ambiguous_option(self):
        with self.assertRaisesRegex(ParserFailureException, r'ambiguous option: --su could match .*'):
            self.validator.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --su 10.0.0.0/24')
        with self.assertRaises(AmbiguousOptionException):
            self.validator.validate_separate_command('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--su'])
        self.validator.validate_separate_command('az group list', ['--out'])

    def test_subscription(self):
        self.validator.validate_command('az account set -s sss')
        self.validator.validate_command('az group list --subscription sss')
        self.validator.validate_separate_command('az account set', ['-s'])
        self.validator.validate_separate_command('az group list', ['--subscription'])

    def test_inner_json(self):
        self.validator.validate_command('az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0 --name CustomScript --resource-group myResourceGroupAG --vmss-name myvmss --settings \'{ "fileUris": ["https://raw.githubusercontent.com/Azure/azure-docs-powershell-samples/master/application-gateway/iis/install_nginx.sh"], "commandToExecute": "./install_nginx.sh" }\'')

    def test_complex_query(self):
        self.validator.validate_command('az webapp deployment list-publishing-profiles --name $webapp --resource-group $resourceGroup --query "[?contains(publishMethod, \'FTP\')].[publishUrl,userName,userPWD]" --output tsv')

    def test_dollar_expression(self):
        self.validator.validate_command('az ad sp create-for-rbac --name $ACR_NAME --scopes $(az acr show -n n -g g --query id --output tsv) --role acrpull')

    def test_sub_command(self):
        self.validator.validate_command('az keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show -n n -g g --query password --output tsv) --role acrpull)')


class TestCommandInfo(unittest.TestCase):
    def test_extract_sub_command(self):
        info = CommandInfo(None, 'vm', 'ad sp create-for-rbac --name $ACR_NAME --scopes $(az acr show --query id --output tsv) --role acrpull'.split())
        self.assertEqual(info.sub_commands[0], 'az acr show --query id --output tsv')

    def test_nested(self):
        info = CommandInfo(None, 'vm', 'keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show --query password --output tsv) --role acrpull)'.split())
        self.assertEqual(info.sub_commands[0], 'az ad sp create-for-rbac --scopes $(az acr show --query password --output tsv) --role acrpull')

    def test_error(self):
        with self.assertRaises(UnmatchedBracketsException):
            CommandInfo(None, 'vm', 'keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show --query password --output tsv) --role acrpull'.split())

    def test_merged_param(self):
        info = CommandInfo(None, 'vm', 'keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show --query password --output tsv) --role acrpull)'.split())
        self.assertEqual(info.parameters[8], '$(az ad sp create-for-rbac --scopes $(az acr show --query password --output tsv) --role acrpull)')
