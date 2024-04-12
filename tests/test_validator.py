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
            'Fail to Parse command: No closing quotation')

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

    def test_script(self):
        script = "#!/bin/bash\n\n# Define variables\n_artifactsLocation=\"[deployment().properties.templateLink.uri]\"\n_artifactsLocationSasToken=\"\"\ndnsLabelPrefix=\"zytest\"\nadminUsername=\"azureuser\"\nimagePublisher=\"openlogic\"\nimageOffer=\"CentOS\"\nimageSku=\"7.2\"\nsshPublicKey=\"zytest\"\nmountFolder=\"/data\"\nnodeSize=\"Standard_D2s_v3\"\ndockerVer=\"1.12\"\ndockerComposeVer=\"1.9.0-rc2\"\ndockerMachineVer=\"0.8.2\"\ndataDiskSize=10\nmasterVMName=\"centos\"\nnumDataDisks=4\nlocation=\"westus\"\n\n# Create availability set\naz vm availability-set create --name avSet -g rg --location $location --platform-fault-domain-count 2 --platform-update-domain-count 5\n\n# Create network security group\naz network nsg create --name default-NSG --location $location\naz network nsg rule create --name default-allow-22 --nsg-name default-NSG --priority 1000 --access Allow --direction Inbound --destination-port-ranges 22 --protocol Tcp --source-address-prefixes \"*\" --source-port-ranges \"*\" --destination-address-prefixes \"*\"\n\n# Create virtual network\naz network vnet create --name virtualnetwork --location $location --address-prefix 10.0.0.0/16\naz network vnet subnet create --name dse --vnet-name virtualnetwork --address-prefix 10.0.0.0/24 --network-security-group default-NSG\n\n# Create public IP address\naz network public-ip create --name publicips --location $location --dns-name $dnsLabelPrefix --allocation-method Dynamic\n\n# Create network interface\naz network nic create --name nic --location $location --vnet-name virtualnetwork --subnet dse --ip-forwarding --public-ip-address \\\npublicips --private-ip-address 10.0.0.254\n\n# Create virtual machine\naz vm create --name $masterVMName --location $location --availability-set avSet --size $nodeSize --image $imagePublisher:$imageOffer:$imageSku:latest --admin-username $adminUsername --ssh-key-value $sshPublicKey --nics nic --os-disk-name ${masterVMName}_OSDisk --os-disk-caching ReadWrite --data-disk-sizes-gb $dataDiskSize --data-disk-caching ReadWrite\n\n# Add extension to virtual machine\naz vm extension set --publisher Microsoft.Azure.Extensions --version 2.0 --name CustomScript --vm-name $masterVMName --settings \"{\"fileUris\": [\"\"$_artifactsLocation\"\"], \"commandToExecute\": \"bash azuredeploy.sh \"$masterVMName\" \"$mountFolder\" \"$numDataDisks\" \"$dockerVer\" \"$dockerComposeVer\" \"$adminUsername\" \"$imageSku\" \"$dockerMachineVer\"\"]}\""
        result = self.validator.validate_script(script)
        self.assertTrue(result[0].result.is_valid)
        self.assertFalse(result[1].result.is_valid)
        self.assertFalse(result[2].result.is_valid)
        self.assertFalse(result[3].result.is_valid)
        self.assertFalse(result[4].result.is_valid)
        self.assertEqual(len(result), 9)
        print()

    def test_dollar_expression(self):
        result = self.validator.validate_script('az ad sp create-for-rbac --name $ACR_NAME --scopes $(az acr show -n n -g g --query id --output tsv) --role acrpull')
        self.assertTrue(result[0].result.is_valid)
        self.assertTrue(result[1].result.is_valid)

    def test_sub_command(self):
        result = self.validator.validate_script('az keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show -n n -g g --query password --output tsv) --role acrpull)')
        self.assertTrue(result[0].result.is_valid)
        self.assertTrue(result[1].result.is_valid)
        self.assertTrue(result[2].result.is_valid)
