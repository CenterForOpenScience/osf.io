import pytest
import mock
from tests.base import OsfTestCase, fake
from osf_tests.factories import AuthUserFactory, ProjectFactory, fake_email
from website.util import api_url_for
from nose.tools import *  # noqa PEP8 asserts
from framework.auth.exceptions import MergeDisableError
from framework.auth import Auth

@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestUpdateUser(OsfTestCase):

    def setUp(self):
        super(TestUpdateUser, self).setUp()
        self.user = AuthUserFactory()

    @mock.patch('website.views.settings.ENABLE_USER_MERGE', False)
    @mock.patch('osf.models.user.website_settings.ENABLE_USER_MERGE', False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_new_email(self, send_mail):
        url = api_url_for('update_user')
        email = fake_email()
        header = {'id': self.user._id,
                  'emails': [{'address': self.user.username, 'primary': True,
                              'confirmed': True},
                             {'address': email, 'primary': False,
                              'confirmed': False}]}
        res = self.app.put_json(url, header, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('emails', res.json['profile'])
        assert_equal(len(res.json['profile']['emails']), 2)
        assert_equal(send_mail.call_count, 1)

    @mock.patch('website.views.settings.ENABLE_USER_MERGE', False)
    @mock.patch('osf.models.user.website_settings.ENABLE_USER_MERGE', False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_existing_email_merge_disable(self, send_mail):
        url = api_url_for('update_user')
        existing_user = AuthUserFactory()
        header = {'id': self.user._id,
                  'emails': [{'address': self.user.username, 'primary': True,
                              'confirmed': True},
                             {'address': existing_user.username,
                              'primary': False, 'confirmed': False}]}
        res = self.app.put_json(url, header, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in(res.json['message_long'], 'Existing email address')
        assert_equal(send_mail.call_count, 0)

    @mock.patch('website.views.settings.ENABLE_USER_MERGE', False)
    @mock.patch('osf.models.user.website_settings.ENABLE_USER_MERGE', False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_existing_unregistered_email_merge_disable(self, send_mail):
        url = api_url_for('update_user')
        project = ProjectFactory()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=fake_email(),
            auth=Auth(project.creator),
        )
        project.save()

        header = {'id': self.user._id,
                  'emails': [{'address': self.user.username, 'primary': True,
                              'confirmed': True},
                             {'address': unreg_user.username,
                              'primary': False, 'confirmed': False}]}
        res = self.app.put_json(url, header, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in(res.json['message_long'], 'Existing email address')
        assert_equal(send_mail.call_count, 0)

    @mock.patch('website.views.settings.ENABLE_USER_MERGE', True)
    @mock.patch('osf.models.user.website_settings.ENABLE_USER_MERGE', True)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_existing_email_merge_enable(self, send_mail):
        url = api_url_for('update_user')
        existing_user = AuthUserFactory()
        header = {'id': self.user._id,
                  'emails': [{'address': self.user.username,
                              'primary': True, 'confirmed': True},
                             {'address': existing_user.username,
                              'primary': False, 'confirmed': False}]}
        res = self.app.put_json(url, header, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_in('emails', res.json['profile'])
        assert_equal(send_mail.call_count, 1)

@pytest.mark.enable_implicit_clean
class TestMergeUser(OsfTestCase):

    def setUp(self):
        super(TestMergeUser, self).setUp()
        self.user = AuthUserFactory()

    @mock.patch('website.views.settings.ENABLE_USER_MERGE', False)
    @mock.patch('osf.models.user.website_settings.ENABLE_USER_MERGE', False)
    def test_add_new_email(self):
        mergee = AuthUserFactory()
        with self.assertRaises(MergeDisableError):
            self.user.merge_user(mergee)
