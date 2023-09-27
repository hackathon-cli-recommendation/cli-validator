import json
import unittest

from cli_validator.validator import CLIValidator


class CLIValidatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = CLIValidator('test_cache')
        await self.validator.load_metas_async("2.51.0")

    def test_validate(self):
        commands = [
            'az login', 'az account set -s sss', 'az group create -n nnn -l westus',
            'az vmss create -n nnn -g ggg --image microsoftwindowsserver:windowsserver:2019-datacenter-zhcn:latest '
            '--admin-username vmtest --admin-password Test123456789#']
        for command in commands:
            self.assertIsNone(self.validator.validate_command(command))
        self.assertIsNotNone(self.validator.validate_command(
            'az vmss update --resource-group <resource-group-name> --name <vmss-name> '
            '--image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --security-type TrustedLaunch '
            '--enable-vtpm true'))
        self.assertIsNone(self.validator.validate_command('az acr build . --image $imageName --registry $registryName --file Dockerfile --build-arg http_proxy=http://myproxy.com'))

    def test_quota_error(self):
        self.assertEqual(self.validator.validate_command('az group show -n "/subscription/{sub}/resourceGroup/{rg}').msg, 'No closing quotation')

    def test_placeholder(self):
        self.assertIsNone(self.validator.validate_command('az network public-ip create -g $(az group list) -n $name --sku <SKU NAME>'))

    def test_extension_command(self):
        self.assertIsNone(self.validator.validate_command('az devcenter dev project list --endpoint "https://8a40af38-3b4c-4672-a6a4-5e964b1870ed-contosodevcenter.centralus.devcenter.azure.com/"'))

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
        self.assertIsNone(result.items[0].result)
        self.assertIsNone(result.items[0].example_result)
        self.assertIsNone(result.items[1].result)
        self.assertIsNone(result.items[1].example_result)
