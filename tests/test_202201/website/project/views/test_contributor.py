#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views tests for the GakuNin RDM."""

from __future__ import absolute_import

import datetime as dt
from rest_framework import status as http_status
import json
import os
import shutil
import tempfile
import time
import unittest
from future.moves.urllib.parse import quote
import uuid

from flask import request
import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts
from django.utils import timezone
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from api.base import settings as api_settings
from addons.github.tests.factories import GitHubAccountFactory
from addons.wiki.models import WikiPage
from framework.auth import cas, authenticate
from framework.flask import redirect
from framework.auth.core import generate_verification_key
from framework import auth
from framework.auth.campaigns import get_campaigns, is_institution_login, is_native_login, is_proxy_login, campaign_url_for
from framework.auth import Auth
from framework.auth.cas import get_login_url
from framework.auth.exceptions import InvalidTokenError
from framework.auth.utils import impute_names_model, ensure_external_identity_uniqueness
from framework.auth.views import login_and_register_handler
from framework.celery_tasks import handlers
from framework.exceptions import HTTPError, TemplateHTTPError
from framework.transactions.handlers import no_auto_transaction
from website import mailchimp_utils, mails, settings, language
from addons.osfstorage import settings as osfstorage_settings
from osf.models import AbstractNode, NodeLog, QuickFilesNode
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.profile.views import update_osf_help_mails_subscription
from website.project.decorators import check_can_access
from website.project.model import has_anonymous_link
from website.project.signals import contributor_added
from website.project.utils import serialize_node
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
    send_claim_email,
    send_claim_registered_email,
)
from website import views as website_view
from website.project.views.node import _should_show_wiki_widget, _view_project, abbrev_authors
from website.util import api_url_for, web_url_for
from website.util import rubeus
from website.util.metrics import OsfSourceTags, OsfClaimedTags, provider_source_tag, provider_claimed_tag
from website.util.timestamp import userkey_generation, AddTimestamp
from osf.utils import permissions
from osf.models import Comment
from osf.models import OSFUser, Tag
from osf.models import Email, TimestampTask
from tests.base import (
    assert_is_redirect,
    capture_signals,
    fake,
    get_default_metaschema,
    OsfTestCase,
    assert_datetime_equal,
)
from tests.base import test_app as mock_app
from tests.test_cas_authentication import generate_external_user_with_resp, make_external_response
from api_tests.utils import create_test_file
from tests.test_timestamp import create_test_file, create_rdmfiletimestamptokenverifyresult

pytestmark = pytest.mark.django_db

from osf.models import BaseFileNode, NodeRelation, QuickFilesNode, BlacklistedEmailDomain, Guid, RdmUserKey, RdmFileTimestamptokenVerifyResult
from osf_tests.factories import (
    fake_email,
    ApiOAuth2ApplicationFactory,
    ApiOAuth2PersonalTokenFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    InstitutionFactory,
    NodeFactory,
    OSFGroupFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    ProjectWithAddonFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    UserFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
    RegionFactory,
    DraftRegistrationFactory,
)
from osf.models.node import set_project_storage_type
from addons.osfstorage.models import NodeSettings



@pytest.mark.enable_bookmark_creation
class TestProjectViews(OsfTestCase):

    def setUp(self):
        super(TestProjectViews, self).setUp()
        self.user1 = AuthUserFactory()
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1)
        self.auth = self.user1.auth
        self.user2 = AuthUserFactory()
        self.auth2 = self.user2.auth
        # A project has 2 contributors
        self.project = ProjectFactory(
            title='Ham',
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

        self.project2 = ProjectFactory(
            title='Tofu',
            description='Glazed',
            creator=self.user1
        )
        self.project2.add_contributor(self.user2, auth=Auth(self.user1))
        self.project2.save()

    @mock.patch('website.project.views.contributor.finalize_invitation')
    def test_project_contributor_re_invite(self, mock_finalize_invitation):
        url = self.project.api_url_for('project_contributor_re_invite')
        payload = {'guid': self.user2._id}
        self.app.post(url, json.dumps(payload),
                      content_type='application/json',
                      auth=self.auth).maybe_follow()
        self.project.reload()
        mock_finalize_invitation.assert_called()


class TestUserInviteViews(OsfTestCase):
    def setUp(self):
        super(TestUserInviteViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = '/api/v1/project/{0}/invite_contributor/'.format(self.project._primary_key)

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_with_user_has_eppn(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        unreg_user.eppn = 'EPPN'
        project.save()
        claim_url = unreg_user.get_claim_url(project._primary_key, external=True)
        claimer_email = given_email.lower().strip()
        unclaimed_record = unreg_user.get_unclaimed_record(project._primary_key)
        referrer = OSFUser.load(unclaimed_record['referrer_id'])

        send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)

        assert_true(send_mail.called)
        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=referrer,
            node=project,
            claim_url=claim_url,
            email=claimer_email,
            fullname=unclaimed_record['name'],
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            login_by_eppn=False,
        )
        assert_true(unreg_user.eppn in unreg_user.temp_account)

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_with_user_has_not_eppn(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        unreg_user.eppn = None
        project.save()
        claim_url = unreg_user.get_claim_url(project._primary_key, external=True)
        claimer_email = given_email.lower().strip()
        unclaimed_record = unreg_user.get_unclaimed_record(project._primary_key)
        referrer = OSFUser.load(unclaimed_record['referrer_id'])

        send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)

        assert_true(send_mail.called)
        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=referrer,
            node=project,
            claim_url=claim_url,
            email=claimer_email,
            fullname=unclaimed_record['name'],
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            login_by_eppn=False,
        )
        assert_equal(len(unreg_user.temp_account), 9)

    def test_claim_user_activate(self):
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)

        given_email = fake_email()
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(self.project.creator),
        )
        unreg_user.save()

        claim_url = '/user/{uid}/{pid}/claim/activate'.format(
            uid=unreg_user._id,
            pid=self.project._id,
        )
        res = self.app.get(claim_url)
        assert_equal(res.status_code, 200)

class TestConfirmationViewBlockBingPreview(OsfTestCase):

    def setUp(self):

        super(TestConfirmationViewBlockBingPreview, self).setUp()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b'

    def test_claim_user_form_cancel_request(self):
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        project.save()

        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true'
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 302)

    def test_claim_user_form_contributor_is_none(self):
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        claim_url = user.get_claim_url(project._primary_key)
        claim_url = claim_url.replace(user._id, 'abcde')
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true',
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    @mock.patch('osf.models.node.Node.cancel_invite')
    def test_claim_user_form_not_nodes_removed(self, mock):
        mock.return_value = False
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true',
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
