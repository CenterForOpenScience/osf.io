# -*- coding: utf-8 -*-
import httplib as http

from framework.auth.core import Auth

from nose.tools import *  # noqa
from test_log_detail import LogsTestCase
from tests.factories import (
    ProjectFactory,
    PrivateLinkFactory
)

from api.base.settings.defaults import API_BASE

# TODO add tests for other log params


class TestLogContributors(LogsTestCase):

    def test_contributor_added_log_has_contributor_info_in_params(self):
        url = self.url + '{}/'.format(self.log_add_contributor._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        params = res.json['data']['attributes']['params']
        params_node = params['params_node']
        contributors = params['contributors'][0]

        assert_equal(params_node['id'], self.node._id)
        assert_equal(params_node['title'], self.node.title)

        assert_equal(contributors['family_name'], self.user.family_name)
        assert_equal(contributors['full_name'], self.user.fullname)
        assert_equal(contributors['given_name'], self.user.given_name)
        assert_equal(contributors['unregistered_name'], None)

    def test_unregistered_contributor_added_has_contributor_info_in_params(self):
        project = ProjectFactory(creator=self.user)
        project.add_unregistered_contributor('Robert Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        unregistered_contributor = project.contributors[1]
        relevant_log = project.logs[-1]
        url = '/{}logs/{}/'.format(API_BASE, relevant_log._id)
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)

        params = res.json['data']['attributes']['params']
        params_node = params['params_node']
        contributors = params['contributors'][0]

        assert_equal(params_node['id'], project._id)
        assert_equal(params_node['title'], project.title)

        assert_equal(contributors['family_name'], 'Jackson')
        assert_equal(contributors['full_name'], 'Robert Jackson')
        assert_equal(contributors['given_name'], 'Robert')
        assert_equal(contributors['unregistered_name'], 'Robert Jackson')

    def test_params_do_not_appear_on_private_project_with_anonymous_view_only_link(self):

        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.append(self.node)
        private_link.save()

        url = self.url + '{}/'.format(self.log_add_contributor._id)

        res = self.app.get(url, {'view_only': private_link.key}, expect_errors=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_in('attributes', data)
        assert_not_in('params', data['attributes'])
        body = res.body
        assert_not_in(self.user._id, body)


