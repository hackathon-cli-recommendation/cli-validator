import unittest
import os
import shutil

from cli_validator.cmd_meta.loader import fetch_data, load_from_disk, ResourceNotExistException
from cli_validator.cmd_meta.parser import CLIParser, ParserFailureException, ParserHelpException


class LoaderTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.meta_data_dir = 'test_meta'

    def test_fetch_load(self):
        fetch_data('2.50.0', self.meta_data_dir)
        meta = load_from_disk('2.50.0', self.meta_data_dir)
        self.assertNotEqual(len(meta), 0)

    def test_fetch_not_existed(self):
        with self.assertRaises(ResourceNotExistException):
            fetch_data('2.50.10', self.meta_data_dir)

    def tearDown(self) -> None:
        super().tearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)


class ParserTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.meta_data_dir = 'test_meta'
        if not os.path.exists(self.meta_data_dir):
            fetch_data('2.50.0', self.meta_data_dir)
        metas = load_from_disk('2.50.0', self.meta_data_dir)
        global_parser = CLIParser.create_global_parser()
        self.parser = CLIParser(prog='az', parents=[global_parser], add_help=True)
        self.parser.add_subcmd_help()
        for meta in metas.values():
            self.parser.load_meta(meta)

    def test_vm_create(self):
        with self.assertRaisesRegex(ParserFailureException, r'.*the following arguments are required.*-g.*'):
            self.parser.parse_args(['vm', 'create', '-n', 'name'])
        with self.assertRaisesRegex(ParserFailureException, r'.*the following arguments are required.*-n.*'):
            self.parser.parse_args(['vm', 'create', '-g', 'rg'])
        self.parser.parse_args(['vm', 'create', '-g', 'rg', '--name', 'VM_NAME'])
        with self.assertRaisesRegex(ParserFailureException, r'.*unrecognized arguments.*--unknown'):
            self.parser.parse_args(['vm', 'create', '-g', 'rg', '--name', 'VM_NAME', '--unknown'])

    def test_other_commands(self):
        self.parser.parse_args(['group', 'create', '-n', 'n', '-l', 'l'])
        self.parser.parse_args(['group', 'list', '-o', 'tsv'])
        self.parser.parse_args(['group', 'list', '--query', 'a.b[0]'])
        self.parser.parse_args(['vmss', 'create', '-g', 'rg', '--name', 'VMSS_NAME'])
        self.parser.parse_args(['webapp', 'create', '-n', 'n', '-g', 'g', '-p', 'p'])

    def test_help(self):
        self.parser.parse_args([])
        with self.assertRaises(ParserHelpException):
            self.parser.parse_args(['-h'])
        self.parser.parse_args(['help'])
        with self.assertRaises(ParserHelpException):
            self.parser.parse_args(['--help'])
        with self.assertRaises(ParserHelpException):
            self.parser.parse_args(['vm', '-h'])
        with self.assertRaises(ParserHelpException):
            self.parser.parse_args(['vm', 'create', '--help'])

    def tearDown(self) -> None:
        super().tearDown()
        # if os.path.exists(self.meta_data_dir):
        #     shutil.rmtree(self.meta_data_dir)


if __name__ == '__main__':
    unittest.main()
