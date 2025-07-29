# -*- coding: utf-8 -*-
import pytest
from unittest import mock
from framework.auth.core import Auth
from osf_tests.factories import ProjectFactory, UserFactory
from addons.metadata.models import FileMetadata
from tests.base import OsfTestCase
from tests.utils import run_celery_tasks
import website.search.search as search
from website.search import elastic_search
from website.search.util import build_query


def query_metadata(term):
    results = search.search(build_query(term), index=elastic_search.INDEX, ext=True, private=True)
    return results


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
@mock.patch('addons.metadata.models.sync_metadata_asset_pool.apply_async')
class TestFileMetadataSearch(OsfTestCase):

    def setUp(self, mock_sync_task=None):
        super(TestFileMetadataSearch, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)

    def test_file_metadata_created_and_searchable(self, _mock_sync_task):
        with run_celery_tasks():
            user = UserFactory()
            project = ProjectFactory(creator=user, is_public=True)
            auth = Auth(user)
            metadata_addon = project.get_or_add_addon('metadata', auth=auth)
            metadata_addon.save()

            osfstorage_addon = project.get_addon('osfstorage')
            root_node = osfstorage_addon.get_root()
            file_node = root_node.append_file('test_file.txt')
            file_node.save()

            unique_search_term = 'created_metadata_test_12345'
            FileMetadata.objects.create(
                project=metadata_addon,
                creator=user,
                user=user,
                path='osfstorage/test_file.txt',
                hash='abc123',
                folder=False,
                metadata='{"items": [{"active": true, "schema": "test_schema", "data": {"title": {"value": "' + unique_search_term + '"}}}]}',
            )

        results = query_metadata(unique_search_term)
        assert len(results['results']) == 1
        assert any(
            result.get('category') == 'metadata' and unique_search_term in result.get('text', '')
            for result in results['results']
        )

    def test_file_metadata_updated_and_searchable(self, _mock_sync_task):
        with run_celery_tasks():
            user = UserFactory()
            project = ProjectFactory(creator=user, is_public=True)
            auth = Auth(user)
            metadata_addon = project.get_or_add_addon('metadata', auth=auth)
            metadata_addon.save()

            osfstorage_addon = project.get_addon('osfstorage')
            root_node = osfstorage_addon.get_root()
            file_node = root_node.append_file('updatable_file.txt')
            file_node.save()

            initial_search_term = 'initial_content_67890'
            file_metadata = FileMetadata.objects.create(
                project=metadata_addon,
                creator=user,
                user=user,
                path='osfstorage/updatable_file.txt',
                hash='def456',
                folder=False,
                metadata='{"items": [{"active": true, "schema": "test_schema", "data": {"title": {"value": "' + initial_search_term + '"}}}]}',
            )

            updated_search_term = 'updated_content_54321'
            file_metadata.metadata = '{"items": [{"active": true, "schema": "test_schema", "data": {"title": {"value": "' + updated_search_term + '"}}}]}'
            file_metadata.save()

        results = query_metadata(updated_search_term)
        assert len(results['results']) == 1
        assert any(
            result.get('category') == 'metadata' and updated_search_term in result.get('text', '')
            for result in results['results']
        )

        # Test that the old content is no longer found
        old_results = query_metadata(initial_search_term)
        assert len(old_results['results']) == 0

    def test_file_metadata_deleted_and_not_searchable(self, _mock_sync_task):
        with run_celery_tasks():
            user = UserFactory()
            project = ProjectFactory(creator=user, is_public=True)
            auth = Auth(user)
            metadata_addon = project.get_or_add_addon('metadata', auth=auth)
            metadata_addon.save()

            osfstorage_addon = project.get_addon('osfstorage')
            root_node = osfstorage_addon.get_root()
            file_node = root_node.append_file('deletable_file.txt')
            file_node.save()

            delete_test_term = 'delete_test_content_99999'
            file_metadata = FileMetadata.objects.create(
                project=metadata_addon,
                creator=user,
                user=user,
                path='osfstorage/deletable_file.txt',
                hash='delete123',
                folder=False,
                metadata='{"items": [{"active": true, "schema": "test_schema", "data": {"title": {"value": "' + delete_test_term + '"}}}]}',
            )

        # Verify the metadata can be found before deletion
        pre_delete_results = query_metadata(delete_test_term)
        assert len(pre_delete_results['results']) == 1
        assert any(
            result.get('category') == 'metadata' and delete_test_term in result.get('text', '')
            for result in pre_delete_results['results']
        )

        with run_celery_tasks():
            # Use the same deletion method as the actual API
            metadata_addon.delete_file_metadata(file_metadata.path, auth=auth)

        post_delete_results = query_metadata(delete_test_term)
        assert len(post_delete_results['results']) == 0
