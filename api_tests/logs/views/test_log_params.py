import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    PrivateLinkFactory,
)
from test_log_detail import LogsTestCase

# TODO add tests for other log params

@pytest.mark.django_db
class TestLogContributors(LogsTestCase):

    def test_contributor_added_log_has_contributor_info_in_params(self, app, node_private, contributor_log_private, url_logs, user_one):
        url = '{}{}/'.format(url_logs, contributor_log_private._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        params = res.json['data']['attributes']['params']
        params_node = params['params_node']
        contributors = params['contributors'][0]

        assert params_node['id'] == node_private._id
        assert params_node['title'] == node_private.title

        assert contributors['family_name'] == user_one.family_name
        assert contributors['full_name'] == user_one.fullname
        assert contributors['given_name'] == user_one.given_name
        assert contributors['unregistered_name'] is None

    def test_unregistered_contributor_added_has_contributor_info_in_params(self, app, user_one):
        project = ProjectFactory(creator=user_one)
        project.add_unregistered_contributor('Robert Jackson', 'robert@gmail.com', auth=Auth(user_one), save=True)
        relevant_log = project.logs.latest()
        url = '/{}logs/{}/'.format(API_BASE, relevant_log._id)
        res = app.get(url, auth=user_one.auth)

        assert res.status_code == 200

        params = res.json['data']['attributes']['params']
        params_node = params['params_node']
        contributors = params['contributors'][0]

        assert params_node['id'] == project._id
        assert params_node['title'] == project.title

        assert contributors['family_name'] == 'Jackson'
        assert contributors['full_name'] == 'Robert Jackson'
        assert contributors['given_name'] == 'Robert'
        assert contributors['unregistered_name'] == 'Robert Jackson'

    def test_params_do_not_appear_on_private_project_with_anonymous_view_only_link(self, app, url_logs, node_private, contributor_log_private, user_one):

        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.add(node_private)
        private_link.save()

        url = '{}{}/'.format(url_logs, contributor_log_private._id)

        res = app.get(url, {'view_only': private_link.key}, expect_errors=True)
        assert res.status_code == 200
        data = res.json['data']
        assert 'attributes' in data
        assert 'params' not in data['attributes']
        body = res.body
        assert user_one._id not in body
