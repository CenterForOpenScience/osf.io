import json
import pytest
import responses

from api.share.utils import format_registration
from osf.models import CollectionSubmission, SpamStatus

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    CollectionProviderFactory,
    CollectionFactory,
    RegistrationFactory,
)

from website import settings
from website.project.tasks import on_node_updated

from framework.auth.core import Auth


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestNodeShare:

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
        reg = RegistrationFactory(is_public=True)
        reg.archive_jobs.clear()  # if reg.archiving is True it will skip updating SHARE
        return reg

    @pytest.fixture()
    def component_registration(self, node):
        NodeFactory(
            creator=node.creator,
            parent=node,
            title='Title1',
        )
        registration = RegistrationFactory(project=node)
        registration.refresh_from_db()
        return registration.get_nodes()[0]

    def test_update_node_share(self, mock_share, node, user):

        on_node_updated(node._id, user._id, False, {'is_public'})

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']

        assert mock_share.calls[-1].request.headers['Authorization'] == 'Bearer mock-api-token'
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'
        assert graph[0]['creative_work']['@type'] == 'project'

    def test_update_registration_share(self, mock_share, registration, user):
        on_node_updated(registration._id, user._id, False, {'is_public'})

        assert mock_share.calls[-1].request.headers['Authorization'] == f'Bearer mock-api-token'

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graphs = data['data']['attributes']['data']['@graph']
        data = [graph for graph in graphs if graph['@type'] == 'workidentifier'][0]
        assert data['uri'] == f'{settings.DOMAIN}{registration._id}/'
        assert data['creative_work']['@type'] == 'registration'

    def test_update_share_correctly_for_projects(self, mock_share, node, user):
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

        mock_share._calls.reset()  # reset after factory calls
        for i, case in enumerate(cases):
            for attr, value in case['attrs'].items():
                setattr(node, attr, value)
            node.save()

            data = json.loads(mock_share.calls[i].request.body.decode())
            graph = data['data']['attributes']['data']['@graph']
            assert graph[1]['is_deleted'] == case['is_deleted']

    def test_update_share_correctly_for_registrations(self, mock_share, registration, user):
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

        mock_share._calls.reset()  # reset after factory calls
        for i, case in enumerate(cases):
            for attr, value in case['attrs'].items():
                setattr(registration, attr, value)
            registration.save()

            assert registration.is_registration
            data = json.loads(mock_share.calls[i].request.body.decode())
            graph = data['data']['attributes']['data']['@graph']
            payload = next((item for item in graph if 'is_deleted' in item.keys()))
            assert payload['is_deleted'] == case['is_deleted']

    def test_format_registration_gets_parent_hierarchy_for_component_registrations(self, project, component_registration, user):
        graph = format_registration(component_registration)

        parent_relation = [i for i in graph if i['@type'] == 'ispartof'][0]
        parent_work_identifier = [i for i in graph if 'creative_work' in i and i['creative_work']['@id'] == parent_relation['subject']['@id']][0]

        # Both must exist to be valid
        assert parent_relation
        assert parent_work_identifier

    def test_update_share_correctly_for_projects_with_qa_tags(self, mock_share, node, user):
        node.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        on_node_updated(node._id, user._id, False, {'is_public'})
        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is True

        node.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is False

    def test_update_share_correctly_for_registrations_with_qa_tags(self, mock_share, registration, user):
        registration.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        on_node_updated(registration._id, user._id, False, {'is_public'})
        data = json.loads(mock_share.calls[-1].request.body.decode())

        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is True

        registration.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is False

    def test_update_share_correctly_for_projects_with_qa_titles(self, mock_share, node, user):
        node.title = settings.DO_NOT_INDEX_LIST['titles'][0] + ' arbitary text for test title.'
        node.save()
        on_node_updated(node._id, user._id, False, {'is_public'})
        data = json.loads(mock_share.calls[-1].request.body.decode())

        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is True

        node.title = 'Not a qa title'
        node.save()
        assert node.title not in settings.DO_NOT_INDEX_LIST['titles']

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is False

    def test_update_share_correctly_for_registrations_with_qa_titles(self, mock_share, registration, user):
        registration.title = settings.DO_NOT_INDEX_LIST['titles'][0] + ' arbitary text for test title.'
        registration.save()

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is True

        registration.title = 'Not a qa title'
        registration.save()
        assert registration.title not in settings.DO_NOT_INDEX_LIST['titles']

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        payload = next((item for item in graph if 'is_deleted' in item.keys()))
        assert payload['is_deleted'] is False

    @responses.activate
    def test_skips_no_settings(self, node, user):
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert len(responses.calls) == 0

    def test_call_async_update_on_500_retry(self, mock_share, node, user):
        """This is meant to simulate a temporary outage, so the retry mechanism should kick in and complete it."""
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=500)
        mock_share.add(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=200)

        mock_share._calls.reset()  # reset after factory calls
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert len(mock_share.calls) == 2

        data = json.loads(mock_share.calls[0].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'

        data = json.loads(mock_share.calls[1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'

    def test_call_async_update_on_500_failure(self, mock_share, node, user):
        """This is meant to simulate a total outage, so the retry mechanism should try X number of times and quit."""
        mock_share.assert_all_requests_are_fired = False  # allows it to retry indefinitely
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=500)

        mock_share._calls.reset()  # reset after factory calls
        on_node_updated(node._id, user._id, False, {'is_public'})

        assert len(mock_share.calls) == 6  # first request and five retries
        data = json.loads(mock_share.calls[0].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'

    def test_no_call_async_update_on_400_failure(self, mock_share, node, user):
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=400)

        on_node_updated(node._id, user._id, False, {'is_public'})

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        assert graph[0]['uri'] == f'{settings.DOMAIN}{node._id}/'
