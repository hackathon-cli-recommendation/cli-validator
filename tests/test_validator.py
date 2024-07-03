import unittest

from cli_validator.validator import CLIValidator


class CLIValidatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = CLIValidator()

    async def test_validate(self):
        commands = [
            'az login', 'az account set -s sss', 'az group create -n nnn -l westus',
            'az vmss create -n nnn -g ggg --image microsoftwindowsserver:windowsserver:2019-datacenter-zhcn:latest '
            '--admin-username vmtest --admin-password Test123456789#']
        for command in commands:
            result = await self.validator.validate_command(command)
            self.assertTrue(result.is_valid)
        self.assertFalse((await self.validator.validate_command(
            'az vmss update --resource-group <resource-group-name> --name <vmss-name> '
            '--image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --security-type TrustedLaunch '
            '--enable-vtpm true')).is_valid)
        self.assertTrue((await self.validator.validate_command(
            'az acr build . --image $imageName --registry $registryName --file Dockerfile --build-arg http_proxy=http://myproxy.com')).is_valid)

    async def test_help(self):
        self.assertEqual((await self.validator.validate_command('az help')).error_message, 'The input command is help or `--help`.')
        self.assertEqual((await self.validator.validate_command('az webapp --help')).error_message, 'The input command is help or `--help`.')
        self.assertFalse((await self.validator.validate_command('az webapp unknown --help')).is_valid)
        self.assertEqual((await self.validator.validate_command('az webapp create --help')).error_message, 'The input command is help or `--help`.')
        self.assertTrue((await self.validator.validate_command('az help', no_help=False)).is_valid)
        self.assertTrue((await self.validator.validate_command('az webapp --help', no_help=False)).is_valid)
        self.assertTrue((await self.validator.validate_command('az webapp create --help', no_help=False)).is_valid)
        self.assertFalse((await self.validator.validate_sig_params('az help', [])).is_valid)
        self.assertFalse((await self.validator.validate_sig_params('az webapp', ['--help'])).is_valid)
        self.assertFalse((await self.validator.validate_sig_params('az webapp create', ['--help'])).is_valid)
        self.assertTrue((await self.validator.validate_sig_params('az help', [], no_help=False)).is_valid)
        self.assertTrue((await self.validator.validate_sig_params('az webapp', ['--help'], no_help=False)).is_valid)
        self.assertTrue((await self.validator.validate_sig_params('az webapp create', ['--help'], no_help=False)).is_valid)

    async def test_quota_error(self):
        result = await self.validator.validate_command('az group show -n "/subscription/{sub}/resourceGroup/{rg}')
        self.assertEqual(result.error_message, 'Fail to Parse command: No closing quotation')

    async def test_placeholder(self):
        result = await self.validator.validate_command('az network public-ip create -g $(az group list) -n $name --sku <SKU NAME>')
        self.assertTrue(result.is_valid)

    async def test_extension_command(self):
        result = await self.validator.validate_command('az devcenter dev project list --endpoint "https://8a40af38-3b4c-4672-a6a4-5e964b1870ed-contosodevcenter.centralus.devcenter.azure.com/"')
        self.assertTrue(result.is_valid)

    async def test_signature_with_param(self):
        result = await self.validator.validate_sig_params('az vmss show -o table', ['-g', '-n'])
        self.assertEqual(result.error_message, 'Unknown Command: "az vmss show -o table". Do you mean "az vmss show"?')

    async def test_command_set(self):
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
        result = await self.validator.validate_command_set(command_set)
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(result.items[0].result.is_valid)
        self.assertTrue(result.items[0].example_result.is_valid)
        self.assertFalse(result.items[1].result.is_valid)
        self.assertFalse(result.items[1].example_result.is_valid)

    async def test_script(self):
        script = "#!/bin/bash\n\n# Define variables\nadminUsername=\"zytest\"\nvmName=\"zytest\"\nlocation=\"westus\"\nauthenticationType=\"sshPublicKey\"\nadminPasswordOrKey=\"zytest\"\nvmSize=\"Standard_A1_v2\"\nstorageAccountName=$(echo -n $vmName | md5sum | cut -c 1-24)\"storage\"\nimagePublisher=\"RedHat\"\nimageOffer=\"RHEL\"\nnicName=$(echo -n $vmName | md5sum | cut -c 1-24)\"nic\"\naddressPrefix=\"10.0.0.0/16\"\nsubnetName=\"Subnet\"\nsubnetPrefix=\"10.0.0.0/24\"\nstorageAccountType=\"Standard_LRS\"\npublicIPAddressName=$(echo -n $vmName | md5sum | cut -c 1-24)\"publicip\"\npublicIPAddressType=\"Dynamic\"\nvirtualNetworkName=$(echo -n $vmName | md5sum | cut -c 1-24)\"vnet\"\nnetworkSecurityGroupName=$subnetName\"-nsg\"\n\n# Create storage account\naz storage account create --name $storageAccountName -g rg --location $location --sku $storageAccountType --kind StorageV2\n\n# Create public IP address\naz network public-ip create --name $publicIPAddressName --location $location --allocation-method $publicIPAddressType\n\n# Create network security group\naz network nsg create --name $networkSecurityGroupName --location $location\n\n# Add security rule to the NSG\naz network nsg rule create --nsg-name $networkSecurityGroupName --name default-allow-22 --priority 1000 --access Allow --direction Inbound --destination-port-ranges 22 --protocol Tcp --source-address-prefixes \"*\" --source-port-ranges \"*\" --destination-address-prefixes \"*\"\n\n# Create virtual network\naz network vnet create --name $virtualNetworkName --location $location --address-prefix $addressPrefix --subnet-name $subnetName --subnet-prefix $subnetPrefix --network-security-group $networkSecurityGroupName\n\n# Create network interface\naz network nic create --name $nicName --location $location --vnet-name $virtualNetworkName --subnet $subnetName --public-ip-address $publicIPAddressName\n\n# Create virtual machine\naz vm create --name $vmName --location $location --size $vmSize --admin-username $adminUsername --admin-password $adminPasswordOrKey --authentication-type $authenticationType --image $imagePublisher:$imageOffer:7.8:latest --nics $nicName --storage-sku $storageAccountType --os-disk-name $vmName\"_OSDisk\" --data-disk-sizes-gb 100 100 --boot-diagnostics-storage $storageAccountName\n\n# Enable boot diagnostics\naz vm boot-diagnostics enable --name $vmName --storage $storageAccountName"
        result = await self.validator.validate_script(script)
        self.assertTrue(result[0].result.is_valid)
        self.assertFalse(result[1].result.is_valid)
        self.assertFalse(result[2].result.is_valid)
        self.assertFalse(result[3].result.is_valid)
        self.assertFalse(result[4].result.is_valid)
        self.assertEqual(len(result), 8)

    async def test_dollar_expression(self):
        result = await self.validator.validate_script('az ad sp create-for-rbac --name $ACR_NAME --scopes $(az acr show -n n -g g --query id --output tsv) --role acrpull')
        self.assertTrue(result[0].result.is_valid)
        self.assertTrue(result[1].result.is_valid)

    async def test_sub_command(self):
        result = await self.validator.validate_script('az keyvault secret set --vault-name $AKV_NAME --name $ACR_NAME --value $(az ad sp create-for-rbac --scopes $(az acr show -n n -g g --query password --output tsv) --role acrpull)')
        self.assertTrue(result[0].result.is_valid)
        self.assertTrue(result[1].result.is_valid)
        self.assertTrue(result[2].result.is_valid)

    async def asyncTearDown(self):
        return await super().asyncTearDown()
