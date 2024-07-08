import json
import unittest
from unittest.mock import patch, Mock, AsyncMock

from cli_validator.exceptions import MetadataException
from cli_validator.repo import CoreRepoMetaRetriever, ExtensionMetaRetriever


class LoaderTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()

    async def test_fetch_version(self):
        version = await CoreRepoMetaRetriever.latest_version()
        self.assertRegex(version, r'azure-cli-\d+\.\d+\.\d+')

    async def test_core_command_tree(self):
        core_repo = CoreRepoMetaRetriever('2.51.0')
        tree = await core_repo.command_tree()
        self.assertNotEqual(len(tree.cmd_tree), 0)

    async def test_core_meta_of_vm(self):
        core_repo = CoreRepoMetaRetriever('2.51.0')
        meta = await core_repo.get_module_meta('vm')
        self.assertNotEqual(len(meta), 0)

    async def test_not_existed_version(self):
        core_repo = CoreRepoMetaRetriever('2.51.10')
        with self.assertRaises(MetadataException):
            tree = await core_repo.command_tree()
        with self.assertRaises(MetadataException):
            meta = await core_repo.get_module_meta('vm')

    @patch('cli_validator.repo.utils.retrieve_http')
    async def test_command_tree_cache(self, mock_retrieve_http: Mock):
        mock_retrieve_http.return_value = json.dumps({'core': {}})
        core_repo = CoreRepoMetaRetriever('2.51.0')
        tree = await core_repo.command_tree()
        self.assertEqual(tree.cmd_tree['core'], {})
        self.assertEqual(mock_retrieve_http.call_count, 1)
        tree = await core_repo.command_tree()
        self.assertEqual(mock_retrieve_http.call_count, 1)

        mock_retrieve_http.return_value = json.dumps({'ext': {}})
        core_repo = ExtensionMetaRetriever()
        tree = await core_repo.command_tree()
        self.assertEqual(tree.cmd_tree['ext'], {})
        self.assertEqual(mock_retrieve_http.call_count, 2)
        tree = await core_repo.command_tree()
        self.assertEqual(mock_retrieve_http.call_count, 2)

    @patch('cli_validator.repo.utils.retrieve_list')
    async def test_latest_version(self, mock_retrieve_version_list: AsyncMock):
        mock_retrieve_version_list.return_value = ['azure-cli-2.49.0', 'azure-cli-2.50.0']
        version = await CoreRepoMetaRetriever.latest_version()
        self.assertEqual(version, 'azure-cli-2.50.0')

    async def test_get_full_metas(self):
        core_repo = CoreRepoMetaRetriever(await CoreRepoMetaRetriever.latest_version())
        metas = await core_repo.get_full_metas()
        for meta in metas:
            self.assertNotEqual(len(meta), 0)

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
