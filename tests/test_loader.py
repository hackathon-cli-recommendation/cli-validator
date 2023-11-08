import os
import shutil
import unittest
from unittest.mock import patch

from cli_validator.loader.cmd_meta import fetch_metas, load_metas_from_disk, ResourceNotExistException, load_metas, \
    load_version_index, load_latest_version
from cli_validator.loader.extension import fetch_command_tree


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
        from cli_validator.loader.cmd_meta.aio import load_metas
        metas = await load_metas('2.53.0', self.meta_data_dir)
        self.assertNotEqual(len(metas), 0)

    def test_fetch_version(self):
        self.assertGreater(len(load_version_index(self.meta_data_dir, True)), 20)
        version = load_latest_version(self.meta_data_dir, True)
        self.assertRegex(version, r'\d+\.\d+\.\d+')

    async def test_aio_fetch_version(self):
        from cli_validator.loader.cmd_meta.aio import load_version_index
        self.assertGreater(len(await load_version_index(self.meta_data_dir, True)), 20)

    @patch('cli_validator.loader.cmd_meta.aio.load_version_index')
    async def test_fetch_latest(self, mock_load_version_index: unittest.mock.Mock):
        from cli_validator.loader.cmd_meta.aio import load_metas
        mock_load_version_index.return_value = ['2.49.0', '2.50.0']
        await load_metas(meta_dir=self.meta_data_dir)
        mock_load_version_index.assert_called()

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        if os.path.exists(self.meta_data_dir):
            shutil.rmtree(self.meta_data_dir)
        if os.path.exists(self.tree_data_dir):
            shutil.rmtree(self.tree_data_dir)
