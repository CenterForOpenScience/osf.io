# -*- coding: utf-8 -*-
import httplib as http

from framework.auth.core import Auth

from nose.tools import *  # noqa
from test_log_detail import LogsTestCase
from tests.factories import (
    ProjectFactory,
)

from api.base.settings.defaults import API_BASE


class TestLogContributors(LogsTestCase):

    def test_log_detail_private_logged_in_contributor_can_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)

    def test_log_detail_private_not_logged_in_cannot_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_log_detail_private_non_contributor_cannot_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_log_detail_public_not_logged_in_can_access_logs(self):
        res = self.app.get(self.public_log_contribs_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)

    def test_log_detail_public_non_contributor_can_access_logs(self):
        res = self.app.get(self.public_log_contribs_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)

    def test_disabled_contributors_in_logs_have_all_fields_hidden_but_names(self):
        self.user.is_disabled = True
        self.user.save()

        res = self.app.get(self.public_log_contribs_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        attributes = res.json['data'][0]['attributes']
        assert_equal(attributes['full_name'], self.user.fullname)
        assert_equal(attributes['given_name'], self.user.given_name)
        assert_equal(attributes['middle_names'], self.user.middle_names)
        assert_equal(attributes['family_name'], self.user.family_name)
        assert_equal(attributes['suffix'], None)
        assert_equal(attributes['date_registered'], None)
        assert_equal(attributes['gitHub'], None)
        assert_equal(attributes['scholar'], None)
        assert_equal(attributes['personal_website'], None)
        assert_equal(attributes['twitter'], None)
        assert_equal(attributes['linkedIn'], None)
        assert_equal(attributes['impactStory'], None)
        assert_equal(attributes['orcid'], None)
        assert_equal(attributes['researcherId'], None)
        assert_equal(attributes['researchGate'], None)
        assert_equal(attributes['academiaInstitution'], None)
        assert_equal(attributes['academiaProfileID'], None)
        assert_equal(attributes['baiduScholar'], None)
        assert_equal(res.json['data'][0]['links'], {})
        assert_not_in('relationships', res.json['data'][0])

    def test_unregistered_contributors_return_name_associated_with_project(self):
        project = ProjectFactory(creator=self.user)
        project.add_unregistered_contributor('Robert Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        relevant_log = project.logs[-1]
        url = '/{}logs/{}/contributors/'.format(API_BASE, relevant_log._id)
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['full_name'], 'Robert Jackson')
        assert_equal(res.json['data'][0]['attributes']['unregistered_contributor'], 'Robert Jackson')
