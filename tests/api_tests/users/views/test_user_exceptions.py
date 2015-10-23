# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory

from api.base.settings.defaults import API_BASE


class TestExceptionFormatting(ApiTestCase):
    def setUp(self):

        super(TestExceptionFormatting, self).setUp()

        self.user = AuthUserFactory.build(
            fullname='Martin Luther King Jr.',
            given_name='Martin',
            family_name='King',
            suffix='Jr.',
            social=dict(
                github='userOneGithub',
                scholar='userOneScholar',
                personal='http://www.useronepersonalwebsite.com',
                twitter='userOneTwitter',
                linkedIn='userOneLinkedIn',
                impactStory='userOneImpactStory',
                orcid='userOneOrcid',
                researcherId='userOneResearcherId'
            )
        )
        self.url = '/{}users/{}/'.format(API_BASE, self.user._id)

        self.user_two = AuthUserFactory()

    def test_updates_user_with_no_fullname(self):
        res = self.app.put_json_api(self.url, {'data': {'id': self.user._id, 'type': 'users', 'attributes': {}}}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/attributes/full_name'})
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')

    def test_updates_user_unauthorized(self):
        res = self.app.put_json_api(self.url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': "Authentication credentials were not provided."})

    def test_updates_user_forbidden(self):
        res = self.app.put_json_api(self.url, auth=self.user_two.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'You do not have permission to perform this action.'})

    def test_user_does_not_exist_formatting(self):
        url = '/{}users/{}/'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'Not found.'})

    def test_basic_auth_me_wrong_password(self):
        url = '/{}users/{}/'.format(API_BASE, 'me')
        res = self.app.get(url, auth=(self.user.username, 'nottherightone'), expect_errors=True)
        assert_equal(res.status_code, 401)
