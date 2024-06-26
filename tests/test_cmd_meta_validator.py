import os
import shlex
import shutil
import unittest
from typing import List

from cli_validator.loader.core_repo import CoreRepoLoader
from cli_validator.meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserFailureException, ValidateHelpException, ConfirmationNoYesException, \
    ValidateFailureException, AmbiguousOptionException, UnknownCommandException


class TestCmdChangeValidator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.meta_data_dir = 'test_cache'
        self.core_repo_loader = CoreRepoLoader(os.path.join(self.meta_data_dir, 'core_repo'))
        await self.core_repo_loader.load_async()

    def validate_command(self, command: str, **kwargs):
        cmd_info = self.core_repo_loader.command_tree.parse_command(shlex.split(command))
        if cmd_info.module is None:
            return
        meta = self.core_repo_loader.load_command_meta(cmd_info.signature, cmd_info.module)
        validator = CommandMetaValidator(meta)
        validator.validate_params(cmd_info.parameters, **kwargs)

    def validate_separate(self, signature: str, parameter: List[str], **kwargs):
        cmd_info = self.core_repo_loader.command_tree.parse_command(shlex.split(signature))
        meta = self.core_repo_loader.load_command_meta(cmd_info.signature, cmd_info.module)
        validator = CommandMetaValidator(meta)
        validator.validate_param_keys(parameter, **kwargs)

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

    def test_help(self):
        with self.assertRaises(ValidateFailureException):
            self.validate_command('az webapp unknown --help')
        with self.assertRaises(ValidateHelpException):
            self.validate_command('az webapp create --help')
        self.validate_command('az webapp create --help', no_help=False)
        with self.assertRaises(ValidateHelpException):
            self.validate_separate('az webapp create', ['--help'])
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
        with self.assertRaisesRegex(ValidateFailureException, r'the following arguments are required: --server/-s'):
            self.validate_command('az sql db copy --name $sourceDatabase --resource-group $sourceResourceGroup --dest-name $destinationDatabase --dest-resource-group $destinationResourceGroup --dest-server $destinationServer')
        with self.assertRaisesRegex(ValidateFailureException, r'unrecognized arguments: --ids.*'):
            self.validate_separate('az webapp create', ['--ids', '-p'])
        with self.assertRaises(ValidateFailureException):
            self.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')

    def test_global_parameter(self):
        self.validate_command('az group show -n qinkai-test -o tsv')
        self.validate_separate('az group show', ['-n', '-o'])

    def test_arg_type(self):
        with self.assertRaisesRegex(ParserFailureException, 'argument --port/-p: invalid int value: \'abc\''):
            self.validate_command('az webapp ssh -g rg -n name --port abc')
        self.validate_command('az webapp ssh -g rg -n name --port 8080')

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

    def test_positional(self):
        with self.assertRaisesRegex(ValidateFailureException, r'the following arguments are required: <SOURCE_LOCATION>'):
            self.validate_command('az acr build --registry $acrName --image $imageName --file $dockerfilePath')
        with self.assertRaisesRegex(ValidateFailureException, r'the following arguments are required: <SOURCE_LOCATION>'):
            self.validate_separate('az acr build', ["--registry", "--image", "--file"])
        self.validate_command('az acr build <SOURCE_LOCATION> --registry $acrName --image $imageName --file $dockerfilePath')
        self.validate_separate('az acr build', ["<SOURCE_LOCATION>", "--registry", "--image", "--file"])

    def test_inner_json(self):
        self.validate_command('az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0 --name CustomScript --resource-group myResourceGroupAG --vmss-name myvmss --settings \'{ "fileUris": ["https://raw.githubusercontent.com/Azure/azure-docs-powershell-samples/master/application-gateway/iis/install_nginx.sh"], "commandToExecute": "./install_nginx.sh" }\'')
        # self.validate_command('az resource create --name chatgpt-IntegrationAccount-123456 --resource-group $resourceGroup --location $location --properties {} --resource-type "Microsoft.Logic/integrationAccounts"')

    def test_complex_query(self):
        self.validate_command('az webapp deployment list-publishing-profiles --name $webapp --resource-group $resourceGroup --query "[?contains(publishMethod, \'FTP\')].[publishUrl,userName,userPWD]" --output tsv')

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)
