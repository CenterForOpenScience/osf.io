import json
import pytest
import responses
from unittest.mock import patch

from api.share.utils import serialize_registration
from osf.models import CollectionSubmission, SpamStatus

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


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestNodeShare:

    @pytest.fixture(scope='class', autouse=True)
    def mock_request_identifier_update(self):
        with patch('osf.models.identifiers.IdentifierMixin.request_identifier_update'):
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
        reg = RegistrationFactory(is_public=True)
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

    def test_update_node_share(self, mock_share, node, user):

        on_node_updated(node._id, user._id, False, {'is_public'})

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')

        assert mock_share.calls[-1].request.headers['Authorization'] == 'Bearer mock-api-token'
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'
        assert identifier_node['creative_work']['@type'] == 'project'

    def test_update_registration_share(self, mock_share, registration, user):
        on_node_updated(registration._id, user._id, False, {'is_public'})

        assert mock_share.calls[-1].request.headers['Authorization'] == 'Bearer mock-api-token'

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graphs = data['data']['attributes']['data']['@graph']
        identifiers = [n for n in graphs if n['@type'] == 'workidentifier']
        uris = {i['uri'] for i in identifiers}
        assert uris == {
            f'{settings.DOMAIN}{registration._id}/',
            f'{settings.DOI_URL_PREFIX}{registration.get_identifier_value("doi")}',
        }
        assert all(i['creative_work']['@type'] == 'registration' for i in identifiers)

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
            work_node = next(n for n in graph if n['@type'] == 'project')
            assert work_node['is_deleted'] == case['is_deleted']

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

    def test_serialize_registration_gets_parent_hierarchy_for_component_registrations(self, project, grandchild_registration):
        res = serialize_registration(grandchild_registration)

        graph = res['@graph']

        # all three registrations are present...
        registration_graph_nodes = [n for n in graph if n['@type'] == 'registration']
        assert len(registration_graph_nodes) == 3
        root = next(n for n in registration_graph_nodes if n['title'] == 'Root')
        child = next(n for n in registration_graph_nodes if n['title'] == 'Child')
        grandchild = next(n for n in registration_graph_nodes if n['title'] == 'Grandchild')

        # ...with the correct 'ispartof' relationships among them (grandchild => child => root)
        expected_ispartofs = [
            {
                '@type': 'ispartof',
                'subject': {'@id': grandchild['@id'], '@type': 'registration'},
                'related': {'@id': child['@id'], '@type': 'registration'},
            }, {
                '@type': 'ispartof',
                'subject': {'@id': child['@id'], '@type': 'registration'},
                'related': {'@id': root['@id'], '@type': 'registration'},
            },
        ]
        actual_ispartofs = [n for n in graph if n['@type'] == 'ispartof']
        assert len(actual_ispartofs) == 2
        for expected_ispartof in expected_ispartofs:
            actual_ispartof = [
                n for n in actual_ispartofs
                if expected_ispartof.items() <= n.items()
            ]
            assert len(actual_ispartof) == 1

        # ...and each has an identifier
        for registration_graph_node in registration_graph_nodes:
            workidentifier_graph_nodes = [
                n for n in graph
                if n['@type'] == 'workidentifier'
                and n['creative_work']['@id'] == registration_graph_node['@id']
            ]
            assert len(workidentifier_graph_nodes) == 1

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
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'

        data = json.loads(mock_share.calls[1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'

    def test_call_async_update_on_500_failure(self, mock_share, node, user):
        """This is meant to simulate a total outage, so the retry mechanism should try X number of times and quit."""
        mock_share.assert_all_requests_are_fired = False  # allows it to retry indefinitely
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=500)

        mock_share._calls.reset()  # reset after factory calls
        on_node_updated(node._id, user._id, False, {'is_public'})

        assert len(mock_share.calls) == 6  # first request and five retries
        data = json.loads(mock_share.calls[0].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'

    def test_no_call_async_update_on_400_failure(self, mock_share, node, user):
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=400)

        on_node_updated(node._id, user._id, False, {'is_public'})

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        identifier_node = next(n for n in graph if n['@type'] == 'workidentifier')
        assert identifier_node['uri'] == f'{settings.DOMAIN}{node._id}/'
