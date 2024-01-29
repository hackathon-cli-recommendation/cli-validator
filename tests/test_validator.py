import os
import shutil
import unittest

from cli_validator.validator import CLIValidator


class CLIValidatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.meta_data_dir = 'test_cache'
        self.validator = CLIValidator(self.meta_data_dir)
        await self.validator.load_metas_async("2.51.0")

    def test_validate(self):
        commands = [
            'az login', 'az account set -s sss', 'az group create -n nnn -l westus',
            'az vmss create -n nnn -g ggg --image microsoftwindowsserver:windowsserver:2019-datacenter-zhcn:latest '
            '--admin-username vmtest --admin-password Test123456789#']
        for command in commands:
            self.assertTrue(self.validator.validate_command(command).is_valid)
        self.assertFalse(self.validator.validate_command(
            'az vmss update --resource-group <resource-group-name> --name <vmss-name> '
            '--image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --security-type TrustedLaunch '
            '--enable-vtpm true').is_valid)
        self.assertTrue(self.validator.validate_command(
            'az acr build . --image $imageName --registry $registryName --file Dockerfile --build-arg http_proxy=http://myproxy.com').is_valid)

    def test_help(self):
        self.assertEqual(self.validator.validate_command('az help').error_message, 'The input command is help or `--help`.')
        self.assertEqual(self.validator.validate_command('az webapp --help').error_message, 'The input command is help or `--help`.')
        self.assertFalse(self.validator.validate_command('az webapp unknown --help').is_valid)
        self.assertEqual(self.validator.validate_command('az webapp create --help').error_message, 'The input command is help or `--help`.')
        self.assertTrue(self.validator.validate_command('az help', no_help=False).is_valid)
        self.assertTrue(self.validator.validate_command('az webapp --help', no_help=False).is_valid)
        self.assertTrue(self.validator.validate_command('az webapp create --help', no_help=False).is_valid)
        self.assertFalse(self.validator.validate_sig_params('az help', []).is_valid)
        self.assertFalse(self.validator.validate_sig_params('az webapp', ['--help']).is_valid)
        self.assertFalse(self.validator.validate_sig_params('az webapp create', ['--help']).is_valid)
        self.assertTrue(self.validator.validate_sig_params('az help', [], no_help=False).is_valid)
        self.assertTrue(self.validator.validate_sig_params('az webapp', ['--help'], no_help=False).is_valid)
        self.assertTrue(self.validator.validate_sig_params('az webapp create', ['--help'], no_help=False).is_valid)

    def test_quota_error(self):
        self.assertEqual(
            self.validator.validate_command('az group show -n "/subscription/{sub}/resourceGroup/{rg}').error_message,
            'No closing quotation')

    def test_placeholder(self):
        self.assertTrue(self.validator.validate_command(
            'az network public-ip create -g $(az group list) -n $name --sku <SKU NAME>').is_valid)

    def test_extension_command(self):
        self.assertTrue(self.validator.validate_command(
            'az devcenter dev project list --endpoint "https://8a40af38-3b4c-4672-a6a4-5e964b1870ed-contosodevcenter.centralus.devcenter.azure.com/"').is_valid)

    def test_signature_with_param(self):
        self.assertEqual(self.validator.validate_sig_params('az vmss show -o table', ['-g', '-n']).error_message, 'Unknown Command: "az vmss show -o table". Do you mean "az vmss show"?')

    def test_command_set(self):
        command_set = [
            {
                "command": "az synapse workspace show",
                "arguments": [
                    "--name",
                    "--resource-group",
                    "--query",
                    "--output"
                ],
                "reason": "Get the Synapse workspace information",
                "example": "az synapse workspace show --name $synapseWorkspaceName --resource-group $resourceGroupName --query id --output tsv",
                "result": [],
                "example_result": []
            },
            {
                "command": "az databricks workspace create",
                "arguments": [
                    "--name",
                    "--resource-group",
                    "--location",
                    "--sku",
                    "--custom-parameters"
                ],
                "reason": "Create a Databricks workspace and connect to Synapse",
                "example": "az databricks workspace create --name $databricksWorkspaceName --resource-group $resourceGroupName --location $location --sku Standard --custom-parameters customVirtualNetworkId=$synapseWorkspaceId",
                "result": [],
                "example_result": []
            }
        ]
        result = self.validator.validate_command_set(command_set)
        self.assertEqual(len(result.errors), 0)
        self.assertTrue(result.items[0].result.is_valid)
        self.assertTrue(result.items[0].example_result.is_valid)
        self.assertTrue(result.items[1].result.is_valid)
        self.assertTrue(result.items[1].example_result.is_valid)

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)


class CLIValidatorNoCacheTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = CLIValidator(None)
        await self.validator.load_metas_async("2.51.0")

    def test_validate(self):
        commands = [
            'az login', 'az account set -s sss', 'az group create -n nnn -l westus',
            'az vmss create -n nnn -g ggg --image microsoftwindowsserver:windowsserver:2019-datacenter-zhcn:latest '
            '--admin-username vmtest --admin-password Test123456789#']
        for command in commands:
            self.assertTrue(self.validator.validate_command(command).is_valid)
        self.assertFalse(self.validator.validate_command(
            'az vmss update --resource-group <resource-group-name> --name <vmss-name> '
            '--image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --security-type TrustedLaunch '
            '--enable-vtpm true').is_valid)
        self.assertTrue(self.validator.validate_command(
            'az acr build . --image $imageName --registry $registryName --file Dockerfile --build-arg http_proxy=http://myproxy.com').is_valid)

    def test_placeholder(self):
        self.assertTrue(self.validator.validate_command(
            'az network public-ip create -g $(az group list) -n $name --sku <SKU NAME>').is_valid)

    def test_extension_command(self):
        self.assertTrue(self.validator.validate_command(
            'az devcenter dev project list --endpoint "https://8a40af38-3b4c-4672-a6a4-5e964b1870ed-contosodevcenter.centralus.devcenter.azure.com/"').is_valid)

    def test_signature_with_param(self):
        self.assertEqual(self.validator.validate_sig_params('az vmss show -o table', ['-g', '-n']).error_message, 'Unknown Command: "az vmss show -o table". Do you mean "az vmss show"?')

    def test_command_set(self):
        command_set = [
            {
                "command": "az synapse workspace show",
                "arguments": [
                    "--name",
                    "--resource-group",
                    "--query",
                    "--output"
                ],
                "reason": "Get the Synapse workspace information",
                "example": "az synapse workspace show --name $synapseWorkspaceName --resource-group $resourceGroupName --query id --output tsv",
                "result": [],
                "example_result": []
            },
            {
                "command": "az databricks workspace create",
                "arguments": [
                    "--name",
                    "--resource-group",
                    "--location",
                    "--sku",
                    "--custom-parameters"
                ],
                "reason": "Create a Databricks workspace and connect to Synapse",
                "example": "az databricks workspace create --name $databricksWorkspaceName --resource-group $resourceGroupName --location $location --sku Standard --custom-parameters customVirtualNetworkId=$synapseWorkspaceId",
                "result": [],
                "example_result": []
            }
        ]
        result = self.validator.validate_command_set(command_set)
        self.assertEqual(len(result.errors), 0)
        self.assertTrue(result.items[0].result.is_valid)
        self.assertTrue(result.items[0].example_result.is_valid)
        self.assertTrue(result.items[1].result.is_valid)
        self.assertTrue(result.items[1].example_result.is_valid)

