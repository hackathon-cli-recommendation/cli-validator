from unittest import TestCase

from cli_validator.validator import CLIValidator


class CLIValidatorTestCase(TestCase):
    def setUp(self):
        self.validator = CLIValidator('2.51.0', 'test_cache')

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
