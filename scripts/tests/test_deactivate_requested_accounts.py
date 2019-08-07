# -*- coding: utf-8 -*-

import pytest
import mock

from nose.tools import *  # noqa

from osf_tests.factories import ProjectFactory, AuthUserFactory

from osf.management.commands.deactivate_requested_accounts import deactivate_requested_accounts

from website import mails, settings

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestDeactivateRequestedAccount:

    @pytest.fixture()
    def user_requested_deactivation(self):
        user = AuthUserFactory(requested_deactivation=True)
        user.requested_deactivation = True
        user.save()
        return user

    @pytest.fixture()
    def user_requested_deactivation_with_node(self):
        user = AuthUserFactory(requested_deactivation=True)
        node = ProjectFactory(creator=user)
        node.save()
        user.save()
        return user

    @mock.patch('osf.management.commands.deactivate_requested_accounts.mails.send_mail')
    def test_deactivate_user_with_no_content(self, mock_mail, user_requested_deactivation):

        deactivate_requested_accounts(dry_run=False)
        user_requested_deactivation.reload()

        assert user_requested_deactivation.requested_deactivation
        assert user_requested_deactivation.contacted_deactivation
        assert user_requested_deactivation.is_disabled
        mock_mail.assert_called_with(can_change_preferences=False,
                                     mail=mails.REQUEST_DEACTIVATION_COMPLETE,
                                     to_addr=user_requested_deactivation.username,
                                     contact_email=settings.OSF_CONTACT_EMAIL,
                                     user=user_requested_deactivation)

    @mock.patch('osf.management.commands.deactivate_requested_accounts.mails.send_mail')
    def test_deactivate_user_with_content(self, mock_mail, user_requested_deactivation_with_node):

        deactivate_requested_accounts(dry_run=False)
        user_requested_deactivation_with_node.reload()

        assert user_requested_deactivation_with_node.requested_deactivation
        assert not user_requested_deactivation_with_node.is_disabled
        mock_mail.assert_called_with(can_change_preferences=False,
                                     mail=mails.REQUEST_DEACTIVATION,
                                     to_addr=settings.OSF_SUPPORT_EMAIL,
                                     user=user_requested_deactivation_with_node)

