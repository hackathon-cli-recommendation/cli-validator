import os
import shutil
import unittest

from cli_validator.cmd_meta.loader import fetch_metas, load_metas_from_disk, ResourceNotExistException
from cli_validator.cmd_tree.loader import fetch_command_tree


class LoaderTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.meta_data_dir = 'test_meta'
        self.tree_data_dir = 'test_tree'
        if not os.path.exists(self.tree_data_dir):
            os.mkdir(self.tree_data_dir)

    def test_fetch_load(self):
        fetch_metas('2.50.0', self.meta_data_dir)
        meta = load_metas_from_disk('2.50.0', self.meta_data_dir)
        self.assertNotEqual(len(meta), 0)

    def test_fetch_not_existed(self):
        with self.assertRaises(ResourceNotExistException):
            fetch_metas('2.50.10', self.meta_data_dir)

    def test_fetch_command_tree(self):
        fetch_command_tree('https://aka.ms/azExtCmdTree', os.path.join(self.tree_data_dir, 'ext_command_tree.json'))

    def tearDown(self) -> None:
        super().tearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)
        if os.path.exists(self.tree_data_dir):
            shutil.rmtree(self.tree_data_dir)
