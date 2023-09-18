import unittest

from cli_validator.validator import CLIValidator


class CLIValidatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = CLIValidator('test_cache')
        await self.validator.load_metas_async("2.51.0")

    def test_validate(self):
        result = self.validator.validate([
            'az login', 'az account set -s sss', 'az group create -n nnn -l westus',
            'az vmss create -n nnn -g ggg --image microsoftwindowsserver:windowsserver:2019-datacenter-zhcn:latest '
            '--admin-username vmtest --admin-password Test123456789#'])
        for res in result:
            self.assertTrue(res.no_error)
        self.assertFalse(self.validator.validate_command(
            'az vmss update --resource-group <resource-group-name> --name <vmss-name> '
            '--image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --security-type TrustedLaunch '
            '--enable-vtpm true').no_error)

    def test_extension_command(self):
        self.assertTrue(self.validator.validate_command('az devcenter dev project list --endpoint "https://8a40af38-3b4c-4672-a6a4-5e964b1870ed-contosodevcenter.centralus.devcenter.azure.com/"').no_error)
