import shlex
import unittest
from typing import List

from cli_validator.meta import MetaRetriever
from cli_validator.meta.validator import CommandMetaValidator
from cli_validator.exceptions import ParserException, ValidateHelpException, ConfirmationNoYesException, \
    ValidateException, AmbiguousOptionException, UnknownCommandException


class TestCmdChangeValidator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.meta_retriever = MetaRetriever()

    async def validate_command(self, command: str, **kwargs):
        cmd_meta = await self.meta_retriever.retrieve_meta(shlex.split(command))
        if cmd_meta.module is None:
            return
        validator = CommandMetaValidator(cmd_meta.metadata)
        validator.validate_params(cmd_meta.parameters, **kwargs)

    async def validate_separate(self, signature: str, parameter: List[str], **kwargs):
        cmd_meta = await self.meta_retriever.retrieve_meta(shlex.split(signature))
        validator = CommandMetaValidator(cmd_meta.metadata)
        validator.validate_param_keys(parameter, **kwargs)

    async def test_validate_command(self):
        await self.validate_command('az webapp create -g g -n n -p p')
        await self.validate_command('az vm create -n n --resource-group g')
        with self.assertRaises(ValidateException):
            await self.validate_command('az vm create -n n')
        with self.assertRaises(ParserException):
            await self.validate_command('az vm create -n n -g g --unknown')
        await self.validate_separate('az webapp create', ['-g', '-n', '-p'])
        await self.validate_separate('az vm create', ['-n', '--resource-group'])
        with self.assertRaises(ValidateException):
            await self.validate_separate('az vm create', ['-n'])
        with self.assertRaises(ValidateException):
            await self.validate_separate('az vm create', ['-n', '-g', '--unknown'])

    async def test_help(self):
        with self.assertRaises(UnknownCommandException):
            await self.validate_command('az webapp unknown --help')
        with self.assertRaises(ValidateHelpException):
            await self.validate_command('az webapp create --help')
        await self.validate_command('az webapp create --help', no_help=False)
        with self.assertRaises(ValidateHelpException):
            await self.validate_separate('az webapp create', ['--help'])
        await self.validate_separate('az webapp create', ['--help'], no_help=False)

    async def test_confirmation(self):
        await self.validate_command('az group delete -n n')
        await self.validate_command('az group delete -n n -y')
        with self.assertRaises(ConfirmationNoYesException):
            await self.validate_command('az group delete -n n', non_interactive=True)
        await self.validate_command('az group delete -n n -y', non_interactive=True)
        await self.validate_command('az group delete -n n --yes', non_interactive=True)
        await self.validate_separate('az group delete', ['-n'])
        await self.validate_separate('az group delete', ['-n', '-y'])
        with self.assertRaises(ConfirmationNoYesException):
            await self.validate_separate('az group delete', ['-n'], non_interactive=True)
        await self.validate_separate('az group delete', ['-n', '-y'], non_interactive=True)
        await self.validate_separate('az group delete', ['-n', '--yes'], non_interactive=True)

    async def test_unknown_command(self):
        with self.assertRaises(UnknownCommandException):
            await self.validate_command('az mysql flexible-server vnet create --name myserver --resource-group myResourceGroup --vnet myVnet --subnet mySubnet --delegate Microsoft.DBforMySQL/flexibleServers')
        with self.assertRaises(UnknownCommandException):
            await self.validate_separate('az mysql flexible-server vnet create', ["--name", "--resource-group", "--vnet", "--subnet", "--delegate"])

    async def test_shorthand_syntax(self):
        await self.validate_command('az network route-table create -g g -n n --tag "{a:b,c:d}" --tag e=f')

    async def test_placeholder(self):
        await self.validate_command('az network public-ip create -g g -n n --sku Standard')
        await self.validate_command('az network public-ip create -g $rgName -n $name --sku <SKU_NAME>')
        await self.validate_command('az network public-ip create -g $rgName -n $name --sku "<SKU NAME>"')
        await self.validate_command('az policy assignment create --policy enforce-tagging --name enforce-tagging-assignment --scope /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}')
        
    async def test_validate_command_with_ids(self):
        await self.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx')
        await self.validate_separate('az storage account show', ['--ids'])
        await self.validate_command('az storage account show --ids /subscriptions/xxxxx/resourceGroups/xxxxx/providers/xxxxx/storageAccounts/xxxxx -n xxxxx')
        await self.validate_separate('az storage account show', ['--ids', '-n'])
        with self.assertRaisesRegex(ParserException, r'unrecognized arguments: --ids .*'):
            await self.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx -p xxxxx')
        with self.assertRaisesRegex(ValidateException, r'the following arguments are required: --server/-s'):
            await self.validate_command('az sql db copy --name $sourceDatabase --resource-group $sourceResourceGroup --dest-name $destinationDatabase --dest-resource-group $destinationResourceGroup --dest-server $destinationServer')
        with self.assertRaisesRegex(ValidateException, r'unrecognized arguments: --ids.*'):
            await self.validate_separate('az webapp create', ['--ids', '-p'])
        with self.assertRaises(ValidateException):
            await self.validate_command('az webapp create --ids /subscriptions/xxxxx/resourceGroups/xxxxx/xxxxx')

    async def test_global_parameter(self):
        await self.validate_command('az group show -n qinkai-test -o tsv')
        await self.validate_separate('az group show', ['-n', '-o'])

    async def test_arg_type(self):
        with self.assertRaisesRegex(ParserException, 'argument --port/-p: invalid int value: \'abc\''):
            await self.validate_command('az webapp ssh -g rg -n name --port abc')
        await self.validate_command('az webapp ssh -g rg -n name --port 8080')

    async def test_network(self):
        await self.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --address-prefix 10.0.0.0/8 --subnet-name chatgpt-Subnet-123456 --subnet-prefix 10.0.0.0/24')
        await self.validate_separate('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--subnet-name', '--subnet-prefix'])

    async def test_ambiguous_option(self):
        with self.assertRaisesRegex(ParserException, r'ambiguous option: --su could match .*'):
            await self.validate_command('az network vnet create --name chatgpt-VNet-123456 --resource-group chatgpt-ResourceGroup-123456 --location $location --su 10.0.0.0/24')
        with self.assertRaises(AmbiguousOptionException):
            await self.validate_separate('az network vnet create',  ['--name', '--resource-group', '--location', '--address-prefix', '--su'])
        await self.validate_command('az group list --out tsv')
        await self.validate_separate('az group list', ['--out'])

    async def test_subscription(self):
        await self.validate_command('az account set -s sss')
        await self.validate_command('az group list --subscription sss')
        await self.validate_separate('az account set', ['-s'])
        await self.validate_separate('az group list', ['--subscription'])

    async def test_positional(self):
        with self.assertRaisesRegex(ValidateException, r'the following arguments are required: <SOURCE_LOCATION>'):
            await self.validate_command('az acr build --registry $acrName --image $imageName --file $dockerfilePath')
        with self.assertRaisesRegex(ValidateException, r'the following arguments are required: <SOURCE_LOCATION>'):
            await self.validate_separate('az acr build', ["--registry", "--image", "--file"])
        await self.validate_command('az acr build <SOURCE_LOCATION> --registry $acrName --image $imageName --file $dockerfilePath')
        await self.validate_separate('az acr build', ["<SOURCE_LOCATION>", "--registry", "--image", "--file"])

    async def test_inner_json(self):
        await self.validate_command('az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0 --name CustomScript --resource-group myResourceGroupAG --vmss-name myvmss --settings \'{ "fileUris": ["https://raw.githubusercontent.com/Azure/azure-docs-powershell-samples/master/application-gateway/iis/install_nginx.sh"], "commandToExecute": "./install_nginx.sh" }\'')
        # await self.validate_command('az resource create --name chatgpt-IntegrationAccount-123456 --resource-group $resourceGroup --location $location --properties {} --resource-type "Microsoft.Logic/integrationAccounts"')

    async def test_complex_query(self):
        await self.validate_command('az webapp deployment list-publishing-profiles --name $webapp --resource-group $resourceGroup --query "[?contains(publishMethod, \'FTP\')].[publishUrl,userName,userPWD]" --output tsv')

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
