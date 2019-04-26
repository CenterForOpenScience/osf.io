import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    NodeFactory,
)
from osf.utils import permissions as osf_permissions


@pytest.mark.django_db
class LogsTestCase:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node_private(self, user_one):
        node_private = ProjectFactory(is_public=False)
        node_private.add_contributor(
            user_one,
            permissions=[osf_permissions.READ],
            auth=Auth(node_private.creator),
            log=True, save=True
        )
        return node_private

    @pytest.fixture()
    def node_public(self, user_one):
        node_public = ProjectFactory(is_public=True)
        node_public.add_contributor(
            user_one,
            permissions=[osf_permissions.READ],
            auth=Auth(node_public.creator),
            log=True, save=True
        )
        return node_public

    @pytest.fixture()
    def logs_public(self, node_public):
        return list(node_public.logs.order_by('date'))

    @pytest.fixture()
    def log_public(self, logs_public):
        return logs_public[0]

    @pytest.fixture()
    def contributor_log_public(self, logs_public):
        return logs_public[1]

    @pytest.fixture()
    def logs_private(self, node_private):
        return list(node_private.logs.order_by('date'))

    @pytest.fixture()
    def log_private(self, logs_private):
        return logs_private[0]

    @pytest.fixture()
    def contributor_log_private(self, logs_private):
        return logs_private[1]

    @pytest.fixture()
    def url_node_private_log(self, node_private):
        return '/{}nodes/{}/logs/'.format(API_BASE, node_private._id)

    @pytest.fixture()
    def url_logs(self):
        return '/{}logs/'.format(API_BASE)

    @pytest.fixture()
    def url_log_private_nodes(self, log_private, url_logs):
        return '{}{}/nodes/'.format(url_logs, log_private._id)

    @pytest.fixture()
    def url_log_public_nodes(self, log_public, url_logs):
        return '{}{}/nodes/'.format(url_logs, log_public._id)

    @pytest.fixture()
    def url_log_detail_private(self, log_private, url_logs):
        return '{}{}/'.format(url_logs, log_private._id)

    @pytest.fixture()
    def url_log_detail_public(self, log_public, url_logs):
        return '{}{}/'.format(url_logs, log_public._id)


@pytest.mark.django_db
class TestLogDetail(LogsTestCase):

    def test_log_detail_private(
            self, app, url_log_detail_private,
            user_one, user_two, log_private):
        # test_log_detail_returns_data
        res = app.get(url_log_detail_private, auth=user_one.auth)
        assert res.status_code == 200
        json_data = res.json['data']
        assert json_data['id'] == log_private._id

        # test_log_detail_private_not_logged_in_cannot_access_logs
        res = app.get(url_log_detail_private, expect_errors=True)
        assert res.status_code == 401

        # test_log_detail_private_non_contributor_cannot_access_logs
        res = app.get(
            url_log_detail_private,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403

    def test_log_detail_public(
            self, app, url_log_detail_public,
            log_public, user_two, user_one):
        # test_log_detail_public_not_logged_in_can_access_logs
        res = app.get(url_log_detail_public, expect_errors=True)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == log_public._id

        # test_log_detail_public_non_contributor_can_access_logs
        res = app.get(
            url_log_detail_public,
            auth=user_two.auth, expect_errors=True)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == log_public._id

        # test_log_detail_data_format_api
        res = app.get(
            '{}?format=api'.format(url_log_detail_public),
            auth=user_one.auth)
        assert res.status_code == 200
        assert log_public._id in str(res.body, 'utf-8')


@pytest.mark.django_db
class TestNodeFileLogDetail:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user_one, user_two):
        node = ProjectFactory(creator=user_one)
        node.add_contributor(user_two)
        return node

    @pytest.fixture()
    def component(self, user_one, node):
        return NodeFactory(parent=node, creator=user_one)

    @pytest.fixture()
    def file_component(self, user_one, component):
        return api_utils.create_test_file(target=component, user=user_one)

    @pytest.fixture()
    def url_node_logs(self, node):
        return '/{}nodes/{}/logs/'.format(API_BASE, node._id)

    @pytest.fixture()
    def url_component_logs(self, component):
        return '/{}nodes/{}/logs/'.format(API_BASE, component._id)

    @pytest.fixture()
    def node_with_log(self, node, user_one, file_component, component):
        node.add_log(
            'osf_storage_file_moved',
            auth=Auth(user_one),
            params={
                'node': node._id,
                'project': node.parent_id,
                'path': file_component.materialized_path,
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
                'source': {
                    'materialized': file_component.materialized_path,
                    'addon': 'osfstorage',
                    'node': {
                        '_id': component._id,
                        'url': component.url,
                        'title': component.title,
                    }
                },
                'destination': {
                    'materialized': file_component.materialized_path,
                    'addon': 'osfstorage',
                    'node': {
                        '_id': node._id,
                        'url': node.url,
                        'title': node.title,
                    }
                }
            },
        )
        node.save()
        return node

    @pytest.fixture()
    def node_with_folder_log(self, node, user_one, file_component, component):
        # Node log is added directly to prove that URLs are removed in
        # serialization
        node.add_log(
            'osf_storage_folder_created',
            auth=Auth(user_one),
            params={
                'node': node._id,
                'project': node.parent_id,
                'path': file_component.materialized_path,
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
                'source': {
                    'materialized': file_component.materialized_path,
                    'addon': 'osfstorage',
                    'node': {
                        '_id': component._id,
                        'url': component.url,
                        'title': component.title,
                    }
                }
            },
        )
        node.save()
        return node

    def test_title_visibility_in_file_move(
            self, app, url_node_logs,
            user_two, component, node_with_log):
        # test_title_not_hidden_from_contributor_in_file_move
        res = app.get(url_node_logs, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['params']['destination']['node_title'] == node_with_log.title

        # test_title_hidden_from_non_contributor_in_file_move
        res = app.get(url_node_logs, auth=user_two.auth)
        assert res.status_code == 200
        assert component.title not in res.json['data']
        assert res.json['data'][0]['attributes']['params']['source']['node_title'] == 'Private Component'

    def test_file_log_keeps_url(
            self, app, url_node_logs, user_two, node_with_log
    ):
        res = app.get(url_node_logs, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['params'].get('urls')

    def test_folder_log_url_removal(
            self, app, url_node_logs, user_two
    ):
        res = app.get(url_node_logs, auth=user_two.auth)
        assert res.status_code == 200
        assert not res.json['data'][0]['attributes']['params'].get('urls')
