import shlex
import unittest
from typing import List

from cli_validator.cmd_meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException, \
    ValidateFailureException, AmbiguousOptionException, UnknownCommandException


class TestCmdChangeValidator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.validator = CommandMetaValidator('test_meta')
        await self.validator.load_metas_async('2.50.0')

    def validate_command(self, command: str, **kwargs):
        self.validator.validate_command(shlex.split(command), **kwargs)

    def validate_separate(self, signature: str, parameter: List[str], **kwargs):
        self.validator.validate_separate_command(shlex.split(signature), parameter, **kwargs)

    def test_validate_command(self):
        self.validate_command('az webapp create -g g -n n -p p')
        self.validate_command('az vm create -n n --resource-group g')
        with self.assertRaises(ValidateFailureException):
            self.validate_command('az vm create -n n')
        with self.assertRaises(ParserFailureException):
            self.validate_command('az vm create -n n -g g --unknown')
        self.validate_separate('az webapp create', ['-g', '-n', '-p'])
        self.validate_separate('az vm create', ['-n', '--resource-group'])
        with self.assertRaises(ValidateFailureException):
            self.validate_separate('az vm create', ['-n'])
        with self.assertRaises(ValidateFailureException):
            self.validate_separate('az vm create', ['-n', '-g', '--unknown'])

    def test_signature_with_param(self):
        with self.assertRaises(ValidateFailureException):
            self.validate_separate('az vmss show -o table', ['-g', '-n'])

    def test_help(self):
        with self.assertRaises(ValidateHelpException):
            self.validate_command('az help')
        with self.assertRaises(ValidateHelpException):
            self.validate_command('az webapp --help')
        with self.assertRaises(ValidateFailureException):
            self.validate_command('az webapp unknown --help')
        with self.assertRaises(ValidateHelpException):
            self.validate_command('az webapp create --help')
        self.validate_command('az help', no_help=False)
        self.validate_command('az webapp --help', no_help=False)
        self.validate_command('az webapp create --help', no_help=False)
        with self.assertRaises(ValidateHelpException):
            self.validate_separate('az help', [])
        with self.assertRaises(ValidateHelpException):
            self.validate_separate('az webapp', ['--help'])
        with self.assertRaises(ValidateHelpException):
            self.validate_separate('az webapp create', ['--help'])
        self.validate_separate('az help', [], no_help=False)
        self.validate_separate('az webapp', ['--help'], no_help=False)
        self.validate_separate('az webapp create', ['--help'], no_help=False)

    def test_confirmation(self):
        self.validate_command('az group delete -n n')
        self.validate_command('az group delete -n n -y')
        with self.assertRaises(ConfirmationNoYesException):
            self.validate_command('az group delete -n n', non_interactive=True)
        self.validate_command('az group delete -n n -y', non_interactive=True)
        self.validate_command('az group delete -n n --yes', non_interactive=True)
        self.validate_separate('az group delete', ['-n'])
        self.validate_separate('az group delete', ['-n', '-y'])
        with self.assertRaises(ConfirmationNoYesException):
            self.validate_separate('az group delete', ['-n'], non_interactive=True)
        self.validate_separate('az group delete', ['-n', '-y'], non_interactive=True)
        self.validate_separate('az group delete', ['-n', '--yes'], non_interactive=True)

    def test_unknown_command(self):
        with self.assertRaises(UnknownCommandException):
            self.validate_command('az mysql flexible-server vnet create --name myserver --resource-group myResourceGroup --vnet myVnet --subnet mySubnet --delegate Microsoft.DBforMySQL/flexibleServers')
        with self.assertRaises(UnknownCommandException):
            self.validate_separate('az mysql flexible-server vnet create', ["--name", "--resource-group", "--vnet", "--subnet", "--delegate"])

    def test_shorthand_syntax(self):
        self.validate_command('az network route-table create -g g -n n --tag "{a:b,c:d}" --tag e=f')

    def test_placeholder(self):
        self.validate_command('az network public-ip create -g g -n n --sku Standard')
        self.validate_command('az network public-ip create -g $rgName -n $name --sku <SKU_NAME>')
        self.validate_command('az network public-ip create -g $rgName -n $name --sku "<SKU NAME>"')
        self.validate_command('az policy assignment create --policy enforce-tagging --name enforce-tagging-assignment --scope /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}')
        
    def test_validate_command_with_ids(self):
        self.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx')
        self.validate_separate('az storage account show', ['--ids'])
        self.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx -n xxxxx')
        self.validate_separate('az storage account show', ['--ids', '-n'])
        with self.assertRaisesRegex(ParserFailureException, r'unrecognized arguments: --ids .*'):
            self.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx -p xxxxx')
        with self.assertRaisesRegex(ValidateFailureException, r'unrecognized arguments: --ids.*'):
            self.validate_separate('az webapp create', ['--ids', '-p'])
        with self.assertRaises(ValidateFailureException):
            self.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')

    def test_global_parameter(self):
        self.validate_command('az group show -n qinkai-test -o tsv')
        self.validate_separate('az group show', ['-n', '-o'])

    def test_network(self):
        self.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --address-prefix 10.0.0.0/8 --subnet-name chatgpt-Subnet-123456 --subnet-prefix 10.0.0.0/24')
        self.validate_separate('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--subnet-name', '--subnet-prefix'])

    def test_ambiguous_option(self):
        with self.assertRaisesRegex(ParserFailureException, r'ambiguous option: --su could match .*'):
            self.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --su 10.0.0.0/24')
        with self.assertRaises(AmbiguousOptionException):
            self.validate_separate('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--su'])
        self.validate_command('az group list --out tsv')
        self.validate_separate('az group list', ['--out'])

    def test_subscription(self):
        self.validate_command('az account set -s sss')
        self.validate_command('az group list --subscription sss')
        self.validate_separate('az account set', ['-s'])
        self.validate_separate('az group list', ['--subscription'])

    def test_inner_json(self):
        self.validate_command('az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0 --name CustomScript --resource-group myResourceGroupAG --vmss-name myvmss --settings \'{ "fileUris": ["https://raw.githubusercontent.com/Azure/azure-docs-powershell-samples/master/application-gateway/iis/install_nginx.sh"], "commandToExecute": "./install_nginx.sh" }\'')
        # self.validate_command('az resource create --name chatgpt-IntegrationAccount-123456 --resource-group $resourceGroup --location $location --properties {} --resource-type "Microsoft.Logic/integrationAccounts"')

    def test_complex_query(self):
        self.validate_command('az webapp deployment list-publishing-profiles --name $webapp --resource-group $resourceGroup --query "[?contains(publishMethod, \'FTP\')].[publishUrl,userName,userPWD]" --output tsv')

    # def test_dollar_expression(self):
    #     self.validate_command('az ad sp create-for-rbac --name $ACR_NAME --scopes $(az acr show -n n -g g --query id --output tsv) --role acrpull')
    #
    # def test_sub_command(self):
    #     self.validate_command('az keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show -n n -g g --query password --output tsv) --role acrpull)')