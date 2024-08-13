from unittest.mock import patch

import pytest
import responses
from pytest import mark
from osf.models import CollectionSubmission, SpamStatus, Outcome
from osf.utils.outcomes import ArtifactTypes

from osf_tests.factories import (
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
    ProjectFactory,
    CollectionProviderFactory,
    CollectionFactory,
    RegistrationFactory,
)

from website import settings
from website.project.tasks import on_node_updated

from framework.auth.core import Auth
from api.share.utils import shtrove_ingest_url, sharev2_push_url
from ._utils import expect_ingest_request


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestNodeShare:

    @pytest.fixture(scope='class', autouse=True)
    def _patches(self):
        with patch('osf.models.identifiers.IdentifierMixin.request_identifier_update'):
            with patch.object(settings, 'USE_CELERY', False):
                yield

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def collection(self):
        collection_provider = CollectionProviderFactory()
        return CollectionFactory(provider=collection_provider)

    @pytest.fixture()
    def node_in_collection(self, collection):
        node = ProjectFactory(is_public=True)
        CollectionSubmission(
            guid=node.guids.first(),
            collection=collection,
            creator=node.creator,
        ).save()
        return node

    @pytest.fixture()
    def node(self):
        return ProjectFactory(is_public=True)

    @pytest.fixture()
    def registration(self, node):
        reg = RegistrationFactory(is_public=True, title='〠')
        IdentifierFactory(referent=reg, category='doi')
        reg.archive_jobs.clear()  # if reg.archiving is True it will skip updating SHARE
        return reg

    @pytest.fixture()
    def grandchild_registration(self):
        root_node = NodeFactory(
            title='Root',
        )
        child_node = NodeFactory(
            creator=root_node.creator,
            parent=root_node,
            title='Child',
        )
        NodeFactory(
            creator=root_node.creator,
            parent=child_node,
            title='Grandchild',
        )
        registration = RegistrationFactory(project=root_node)
        registration.refresh_from_db()
        return registration.get_nodes()[0].get_nodes()[0]

    @pytest.fixture()
    def registration_outcome(self, registration):
        o = Outcome.objects.for_registration(registration, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(), artifact_type=ArtifactTypes.DATA, finalized=True
        )
        o.artifact_metadata.create(
            identifier=IdentifierFactory(), artifact_type=ArtifactTypes.PAPERS, finalized=True
        )
        return o

    def test_update_node_share(self, mock_share_responses, node, user):
        with expect_ingest_request(mock_share_responses, node._id):
            on_node_updated(node._id, user._id, False, {'is_public'})

    def test_update_registration_share(self, mock_share_responses, registration, user):
        with expect_ingest_request(mock_share_responses, registration._id):
            on_node_updated(registration._id, user._id, False, {'is_public'})

    def test_update_share_correctly_for_projects(self, mock_share_responses, node, user):
        cases = [{
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': False, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': True, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.SPAM}
        }]

        mock_share_responses._calls.reset()  # reset after factory calls
        for i, case in enumerate(cases):
            for attr, value in case['attrs'].items():
                setattr(node, attr, value)
            with expect_ingest_request(mock_share_responses, node._id, delete=case['is_deleted']):
                node.save()

    def test_update_share_correctly_for_registrations(self, mock_share_responses, registration, user):
        cases = [{
            'is_deleted': True,
            'attrs': {'is_public': False, 'is_deleted': False}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': True}
        }, {
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False}
        }]

        mock_share_responses._calls.reset()  # reset after factory calls
        for i, case in enumerate(cases):
            for attr, value in case['attrs'].items():
                setattr(registration, attr, value)
            with expect_ingest_request(mock_share_responses, registration._id, delete=case['is_deleted']):
                registration.save()
            assert registration.is_registration

    def test_update_share_correctly_for_projects_with_qa_tags(self, mock_share_responses, node, user):
        with expect_ingest_request(mock_share_responses, node._id, delete=True):
            node.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        with expect_ingest_request(mock_share_responses, node._id, delete=False):
            node.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)

    def test_update_share_correctly_for_registrations_with_qa_tags(self, mock_share_responses, registration, user):
        with expect_ingest_request(mock_share_responses, registration._id, delete=True):
            registration.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        with expect_ingest_request(mock_share_responses, registration._id):
            registration.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)

    def test_update_share_correctly_for_projects_with_qa_titles(self, mock_share_responses, node, user):
        node.title = settings.DO_NOT_INDEX_LIST['titles'][0] + ' arbitary text for test title.'
        node.save()
        with expect_ingest_request(mock_share_responses, node._id, delete=True):
            on_node_updated(node._id, user._id, False, {'is_public'})
        node.title = 'Not a qa title'
        with expect_ingest_request(mock_share_responses, node._id):
            node.save()
        assert node.title not in settings.DO_NOT_INDEX_LIST['titles']

    def test_update_share_correctly_for_registrations_with_qa_titles(self, mock_share_responses, registration, user):
        registration.title = settings.DO_NOT_INDEX_LIST['titles'][0] + ' arbitary text for test title.'
        with expect_ingest_request(mock_share_responses, registration._id, delete=True):
            registration.save()
        registration.title = 'Not a qa title'
        with expect_ingest_request(mock_share_responses, registration._id):
            registration.save()
        assert registration.title not in settings.DO_NOT_INDEX_LIST['titles']

    @responses.activate
    def test_skips_no_settings(self, node, user):
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert len(responses.calls) == 0

    @mark.skip('Synchronous retries not supported if celery >=5.0')
    def test_call_async_update_on_500_retry(self, mock_share_responses, node, user):
        """This is meant to simulate a temporary outage, so the retry mechanism should kick in and complete it."""
        mock_share_responses.replace(responses.POST, shtrove_ingest_url(), status=500)
        mock_share_responses.add(responses.POST, shtrove_ingest_url(), status=200)
        mock_share_responses.replace(responses.POST, sharev2_push_url(), status=500)
        mock_share_responses.add(responses.POST, sharev2_push_url(), status=200)
        with expect_ingest_request(mock_share_responses, node._id, count=2):
            on_node_updated(node._id, user._id, False, {'is_public'})

    @mark.skip('Synchronous retries not supported if celery >=5.0')
    def test_call_async_update_on_500_failure(self, mock_share_responses, node, user):
        """This is meant to simulate a total outage, so the retry mechanism should try X number of times and quit."""
        mock_share_responses.replace(responses.POST, shtrove_ingest_url(), status=500)
        mock_share_responses.replace(responses.POST, sharev2_push_url(), status=500)
        with expect_ingest_request(mock_share_responses, node._id, count=5):  # tries five times
            on_node_updated(node._id, user._id, False, {'is_public'})

    @mark.skip('Synchronous retries not supported if celery >=5.0')
    def test_no_call_async_update_on_400_failure(self, mock_share_responses, node, user):
        mock_share_responses.replace(responses.POST, shtrove_ingest_url(), status=400)
        mock_share_responses.replace(responses.POST, sharev2_push_url(), status=400)
        with expect_ingest_request(mock_share_responses, node._id):
            on_node_updated(node._id, user._id, False, {'is_public'})
