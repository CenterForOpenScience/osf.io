
from unittest.mock import ANY

from unittest import mock

import pytest
from rest_framework import status as http_status

from framework.auth import Auth
from framework.exceptions import HTTPError
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from website import mails, settings
from website.profile.utils import add_contributor_json
from website.project.views.contributor import (
    send_claim_email,
)


class TestUserInviteViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = f'/api/v1/project/{self.project._primary_key}/invite_contributor/'

    def test_invite_contributor_post_if_not_in_db(self):
        name, email = fake.name(), fake_email()
        res = self.app.post(
            self.invite_url,
            json={'fullname': name, 'email': email},
            auth=self.user.auth,
        )
        contrib = res.json['contributor']
        assert contrib['id'] is None
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_unreg_already_in_db(self):
        # A n unreg user is added to a different project
        name, email = fake.name(), fake_email()
        project2 = ProjectFactory()
        unreg_user = project2.add_unregistered_contributor(fullname=name, email=email,
                                                           auth=Auth(project2.creator))
        project2.save()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email}, auth=self.user.auth)
        expected = add_contributor_json(unreg_user)
        expected['fullname'] = name
        expected['email'] = email
        assert res.json['contributor'] == expected

    def test_invite_contributor_post_if_email_already_registered(self):
        reg_user = UserFactory()
        name, email = fake.name(), reg_user.username
        # Tries to invite user that is already registered - this is now permitted.
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email},
                                 auth=self.user.auth)
        contrib = res.json['contributor']
        assert contrib['id'] == reg_user._id
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_user_is_already_contributor(self):
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.project.creator)
        )
        self.project.save()
        # Tries to invite unreg user that is already a contributor
        res = self.app.post(self.invite_url,
                                 json={'fullname': fake.name(), 'email': unreg_user.username},
                                 auth=self.user.auth)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_invite_contributor_with_no_email(self):
        name = fake.name()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': None}, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        data = res.json
        assert data['status'] == 'success'
        assert data['contributor']['fullname'] == name
        assert data['contributor']['email'] is None
        assert not data['contributor']['registered']

    def test_invite_contributor_requires_fullname(self):
        res = self.app.post(self.invite_url,
                                 json={'email': 'brian@queen.com', 'fullname': ''}, auth=self.user.auth,
                                 )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_given_email(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)

        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=ANY,
            node=project,
            claim_url=ANY,
            email=unreg_user.email,
            fullname=unreg_user.fullname,
            branded_service=None,
            can_change_preferences=False,
            logo='osf_logo',
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_referrer(self, send_mail):
        project = ProjectFactory()
        referrer = project.creator
        given_email, real_email = fake_email(), fake_email()
        unreg_user = project.add_unregistered_contributor(fullname=fake.name(),
                                                          email=given_email, auth=Auth(
                                                              referrer)
                                                          )
        project.save()
        send_claim_email(email=real_email, unclaimed_user=unreg_user, node=project)

        assert send_mail.called
        # email was sent to referrer
        send_mail.assert_called_with(
            referrer.username,
            mails.FORWARD_INVITE,
            user=unreg_user,
            referrer=referrer,
            claim_url=unreg_user.get_claim_url(project._id, external=True),
            email=real_email.lower().strip(),
            fullname=unreg_user.get_unclaimed_record(project._id)['name'],
            node=project,
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_before_throttle_expires(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        send_mail.reset_mock()
        # 2nd call raises error because throttle hasn't expired
        with pytest.raises(HTTPError):
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        assert not send_mail.called
