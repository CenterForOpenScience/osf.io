# -*- coding: utf-8 -*-
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory
from rest_framework import exceptions


@pytest.mark.django_db
class TestExceptionFormatting:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory(
            fullname='Martin Luther King Jr.',
            given_name='Martin',
            family_name='King',
            suffix='Jr.',
            social=dict(
                github='userOneGithub',
                scholar='userOneScholar',
                profileWebsites=['http://www.useronepersonalwebsite.com'],
                twitter='userOneTwitter',
                linkedIn='userOneLinkedIn',
                impactStory='userOneImpactStory',
                orcid='userOneOrcid',
                researcherId='userOneResearcherId'
            )
        )

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/'.format(API_BASE, user._id)

    def test_user_errors(self, app, user, user_two, url):

    #   test_updates_user_with_no_fullname
        res = app.put_json_api(url, {'data': {'id': user._id, 'type': 'users', 'attributes': {}}}, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert res.json['errors'][0]['source'] == {'pointer': '/data/attributes/full_name'}
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    #   test_updates_user_unauthorized
        res = app.put_json_api(url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': exceptions.NotAuthenticated.default_detail}

    #   test_updates_user_forbidden
        res = app.put_json_api(url, auth=user_two.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': exceptions.PermissionDenied.default_detail}

    #   test_user_does_not_exist_formatting
        url = '/{}users/{}/'.format(API_BASE, '12345')
        res = app.get(url, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': exceptions.NotFound.default_detail}

    #   test_basic_auth_me_wrong_password
        url = '/{}users/{}/'.format(API_BASE, 'me')
        res = app.get(url, auth=(user.username, 'nottherightone'), expect_errors=True)
        assert res.status_code == 401
