import unittest

from cli_validator.cmd_meta.parser import CLIParser, ParserFailureException
from cli_validator.exceptions import ParserHelpException


class ParserTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        meta = {
            "name": "vm create",
            "is_aaz": True,
            "supports_no_wait": True,
            "parameters": [{
                "name": "vm_name",
                "options": ["--name", "-n"],
                "required": True
            }, {
                "name": "resource_group_name",
                "options": ["--resource-group", "-g"],
                "required": True,
                "id_part": "resource_group"
            }, {
                "name": "image",
                "options": ["--image"]
            }, {
                "name": "size",
                "options": ["--size"],
                "default": "Standard_DS1_v2"
            }, {
                "name": "location",
                "options": ["--location", "-l"],
                "type": "custom_type"
            }, {
                "name": "tags",
                "options": ["--tags"],
                "nargs": "*"
            }]
        }
        global_parser = CLIParser.create_global_parser()
        self.parser = CLIParser(prog='az', parents=[global_parser], add_help=True)
        self.parser.load_meta(meta)

    def test_vm_create(self):
        with self.assertRaisesRegex(ParserFailureException, r'.*the following arguments are required.*-g.*'):
            self.parser.parse_args(['-n', 'name'])
        with self.assertRaisesRegex(ParserFailureException, r'.*the following arguments are required.*-n.*'):
            self.parser.parse_args(['-g', 'rg'])
        self.parser.parse_args(['-g', 'rg', '--name', 'VM_NAME'])
        with self.assertRaisesRegex(ParserFailureException, r'.*unrecognized arguments.*--unknown'):
            self.parser.parse_args(['-g', 'rg', '--name', 'VM_NAME', '--unknown'])
        with self.assertRaisesRegex(ParserFailureException, r'argument --query: invalid jmespath_type value:.*'):
            self.parser.parse_args(['-g', 'rg', '--name', 'VM_NAME', '--query', 'dfa.fad[0]daf'])

    def test_help(self):
        with self.assertRaises(ParserHelpException):
            self.parser.parse_args(['--help'])


if __name__ == '__main__':
    unittest.main()
