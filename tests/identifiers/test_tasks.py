import pytest
from unittest import mock
from django.utils import timezone
from celery.exceptions import RetryTaskError

from osf_tests.factories import UserFactory, NodeFactory
from website.identifiers.tasks import task__update_verified_links
from website.identifiers.clients.datacite import DataCiteClient

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user, is_public=True)

@pytest.fixture()
def node_with_doi(user):
    node = NodeFactory(creator=user, is_public=True)
    node.set_identifier_value('doi', '10.1234/test')
    return node

@pytest.fixture()
def mock_datacite_client():
    with mock.patch('website.identifiers.clients.datacite.DataCiteClient') as mock_client:
        mock_instance = mock.Mock(spec=DataCiteClient)
        mock_instance.update_identifier.return_value = {'doi': '10.1234/test'}
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture(autouse=True)
def mock_get_doi_client(mock_datacite_client):
    with mock.patch('osf.models.AbstractNode.get_doi_client', return_value=mock_datacite_client):
        yield

@pytest.mark.enable_enqueue_task
class TestUpdateDOIMetadataWithVerifiedLinks:

    def test_update_doi_metadata_success(self, node_with_doi, mock_datacite_client):
        verified_links = {
            'https://osf.io/': 'Text',
            f'https://osf.io/{node_with_doi._id}/': 'Text'
        }
        node_with_doi.verified_links = verified_links
        node_with_doi.save()

        task__update_verified_links.delay(node_with_doi._id)

        node_with_doi.reload()
        assert node_with_doi.verified_links == verified_links
        mock_datacite_client.update_identifier.assert_called_once_with(node_with_doi, 'doi')

    def test_update_doi_metadata_no_doi_no_create(self, node, mock_datacite_client):
        task__update_verified_links.delay(node._id)
        mock_datacite_client.update_identifier.assert_not_called()


    @mock.patch('framework.sentry.log_message')
    @mock.patch('website.identifiers.tasks.task__update_verified_links.retry')
    def test_update_doi_metadata_deleted_node(self, mock_retry, mock_sentry_log, node_with_doi, mock_datacite_client):
        node_with_doi.is_deleted = True
        node_with_doi.deleted = timezone.now()
        node_with_doi.save()

        mock_datacite_client.update_identifier.side_effect = Exception('Node is deleted')
        mock_retry.side_effect = Exception('Retry prevented')

        with pytest.raises(Exception, match='Retry prevented'):
            task__update_verified_links.delay(node_with_doi._id)

        mock_sentry_log.assert_called_with(
            'Failed to update DOI metadata with verified links',
            extra_data={'guid': node_with_doi._id, 'error': mock.ANY},
            level=mock.ANY
        )

    @mock.patch('website.identifiers.tasks.task__update_verified_links.retry')
    def test_update_doi_metadata_exception_retry(self, mock_retry, node_with_doi, mock_datacite_client):
        mock_datacite_client.update_identifier.side_effect = Exception('Test error')
        mock_retry.side_effect = RetryTaskError()

        with pytest.raises(RetryTaskError):
            task__update_verified_links.delay(node_with_doi._id)

        mock_datacite_client.update_identifier.assert_called_once_with(node_with_doi, 'doi')
        mock_retry.assert_called_once_with(exc=mock.ANY)



    def test_update_doi_metadata_with_multiple_verified_links(self, node_with_doi, mock_datacite_client):
        verified_links = {
            'https://osf.io/': 'Text',
            f'https://osf.io/{node_with_doi._id}/': 'Text',
            'https://example.com': 'Text',
            'https://test.org': 'Text'
        }
        node_with_doi.verified_links = verified_links
        node_with_doi.save()

        task__update_verified_links.delay(node_with_doi._id)

        node_with_doi.reload()
        assert node_with_doi.verified_links == verified_links
        mock_datacite_client.update_identifier.assert_called_once_with(node_with_doi, 'doi')

    def test_update_doi_metadata_private_node(self, node_with_doi, mock_datacite_client):
        node_with_doi.is_public = False
        node_with_doi.save()
        mock_datacite_client.reset_mock()

        task__update_verified_links.delay(node_with_doi._id)

        mock_datacite_client.update_identifier.assert_called_once_with(node_with_doi, 'doi')
