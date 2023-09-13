import os
import shutil
import unittest

from cli_validator.cmd_meta.loader import fetch_metas, load_metas_from_disk, ResourceNotExistException, load_metas
from cli_validator.cmd_tree.loader import fetch_command_tree


class LoaderTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.meta_data_dir = 'test_meta'
        self.tree_data_dir = 'test_tree'
        if not os.path.exists(self.tree_data_dir):
            os.mkdir(self.tree_data_dir)

    def test_fetch_load(self):
        fetch_metas('2.50.0', self.meta_data_dir)
        meta = load_metas_from_disk('2.50.0', self.meta_data_dir)
        self.assertNotEqual(len(meta), 0)

    def test_load_metas(self):
        meta = load_metas('2.50.0', self.meta_data_dir)
        self.assertNotEqual(len(meta), 0)

    def test_fetch_not_existed(self):
        with self.assertRaises(ResourceNotExistException):
            fetch_metas('2.50.10', self.meta_data_dir)

    def test_fetch_command_tree(self):
        fetch_command_tree('https://aka.ms/azExtCmdTree', os.path.join(self.tree_data_dir, 'ext_command_tree.json'))

    async def test_aio_load(self):
        from cli_validator.cmd_meta.loader.aio import load_metas
        metas = await load_metas('2.51.0')
        self.assertNotEqual(len(metas), 0)

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)
        if os.path.exists(self.tree_data_dir):
            shutil.rmtree(self.tree_data_dir)
