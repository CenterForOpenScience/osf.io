from __future__ import absolute_import
from rest_framework import status as http_status
import pytest
import mock
from nose.tools import *
from website.profile.views import _profile_view
from website.util import api_url_for
from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory

pytestmark = pytest.mark.django_db


@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
@pytest.mark.skip('Clone test case from website/profile/views.py '
                  'for making coverage')
class TestUserProfile(OsfTestCase):

    def setUp(self):
        super(TestUserProfile, self).setUp()
        self.user = AuthUserFactory()

    @mock.patch('website.settings.ENABLE_USER_MERGE', False)
    def test_user_update_not_temp_account(self):
        user1 = AuthUserFactory(fullname='fullname_1')
        user2 = AuthUserFactory(fullname='fullname_2')
        email_1 = 'test@cos.io'
        email_2 = 'abcd@csp.com'
        user2.emails.create(address=email_2)

        url = api_url_for('update_user', user1._id)

        header = {
            'id': user1._id,
            'emails': [
                {'address': email_1},
                {'address': email_2},
                {'address': user1.username},
            ]
        }

        res = self.app.put_json(url, header, auth=user1.auth,
                                expect_errors=True)

        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)
        assert_not_equal(res.json['message_long'], None)

    @mock.patch('website.settings.ENABLE_USER_MERGE', False)
    def test_user_update_has_temp_account(self):
        user1 = AuthUserFactory(fullname='fullname_1')
        user2 = AuthUserFactory(fullname='fullname_2')
        email_1 = 'test_1@cos.io'
        email_2 = 'abc@scp.com'
        user2.emails.create(address=email_2)
        user2.temp_account = True
        user2.save()

        url = api_url_for('update_user', user1._id)

        header = {
            'id': user1._id,
            'emails': [
                {'address': email_1},
                {'address': email_2},
                {'address': user1.username},
            ]
        }

        res = self.app.put_json(url, header, auth=user1.auth)

        assert_equal(res.status_code, http_status.HTTP_200_OK)
        assert_equal(len(res.json['profile']['emails']), 2)
        assert_equal(res.json['user']['_id'], user1._id)
        assert_true(res.json['user']['is_profile'])

    def test_user_update_temp_user_not_exist(self):
        user1 = AuthUserFactory(fullname='fullname_1')
        email_1 = 'andy@cos.vn'
        email_2 = 'wis@csp.com'

        url = api_url_for('update_user', user1._id)

        header = {
            'id': user1._id,
            'emails': [
                {'address': email_1, 'confirmed': True, 'primary': True},
                {'address': email_2},
                {'address': user1.username},
            ]
        }

        res = self.app.put_json(url, header, auth=user1.auth,
                                expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_profile_view_has_temp_user(self):
        user1 = AuthUserFactory(fullname='fullname_1')
        user2 = AuthUserFactory(fullname='fullname_2')
        email_2 = 'luk@com.vn'
        user2.emails.create(address=email_2)

        res = _profile_view(user1, is_profile=True, temp_user=user2)

        assert_equal(res['profile']['id'], user1._id)
        assert_equal(res['profile']['fullname'], user1.fullname)
        assert_equal(res['profile']['inactive_profile']['id'], user2._id)
        assert_equal(res['profile']['inactive_profile']['fullname'],
                     user2.fullname)
