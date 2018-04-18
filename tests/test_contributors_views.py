# -*- coding: utf-8 -*-

import time
import datetime
from nose.tools import *  # noqa; PEP8 asserts

from osf_tests.factories import ProjectFactory, NodeFactory, AuthUserFactory, NodeRequestFactory
from osf.utils import workflows
from tests.base import OsfTestCase

from framework.auth.decorators import Auth

from website.profile import utils


class TestContributorUtils(OsfTestCase):

    def setUp(self):
        super(TestContributorUtils, self).setUp()
        self.project = ProjectFactory()

    def test_serialize_user(self):
        serialized = utils.serialize_user(self.project.creator, self.project)
        assert_true(serialized['visible'])
        assert_equal(serialized['permission'], 'admin')

    def test_serialize_user_full_does_not_include_emails_by_default(self):
        serialized = utils.serialize_user(self.project.creator, self.project, full=True)
        assert_not_in('emails', serialized)

    def test_serialize_user_full_includes_email_if_is_profile(self):
        serialized = utils.serialize_user(
            self.project.creator,
            self.project,
            full=True,
            is_profile=True
        )
        assert_in('emails', serialized)

    def test_serialize_user_admin(self):
        serialized = utils.serialize_user(self.project.creator, self.project, admin=True)
        assert_false(serialized['visible'])
        assert_equal(serialized['permission'], 'read')

    def test_serialize_access_requests(self):
        new_user = AuthUserFactory()
        node_request = NodeRequestFactory(
            creator=new_user,
            target=self.project,
            request_type=workflows.RequestTypes.ACCESS.value,
            machine_state=workflows.DefaultStates.INITIAL.value
        )
        node_request.run_submit(new_user)
        res = utils.serialize_access_requests(self.project)

        assert len(res) == 1
        assert res[0]['comment'] == node_request.comment
        assert res[0]['id'] == node_request._id
        assert res[0]['user'] == utils.serialize_user(new_user)


class TestContributorViews(OsfTestCase):

    def setUp(self):
        super(TestContributorViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def test_get_contributors_no_limit(self):
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=False,
        )
        self.project.save()
        url = self.project.api_url_for('get_contributors')
        res = self.app.get(url, auth=self.user.auth)
        # Should be two visible contributors on the project
        assert_equal(
            len(res.json['contributors']),
            2,
        )

    def test_get_contributors_with_limit(self):
        # Add five contributors
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=False,
        )
        self.project.save()
        # Set limit to three contributors
        url = self.project.api_url_for('get_contributors', limit=3)
        res = self.app.get(url, auth=self.user.auth)
        # Should be three visible contributors on the project
        assert_equal(
            len(res.json['contributors']),
            3,
        )
        # There should be two 'more' contributors not shown
        assert_equal(
            (res.json['more']),
            2,
        )

    def test_get_contributors_from_parent(self):
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            AuthUserFactory(),
            auth=self.auth,
            visible=False,
        )
        component = NodeFactory(parent=self.project, creator=self.user)

        user_already_on_component = AuthUserFactory()
        component.add_contributor(
            user_already_on_component,
            auth=self.auth,
            visible=True,
        )
        self.project.add_contributor(
            user_already_on_component,
            auth=self.auth,
            visible=True,
        )

        self.project.save()
        component.save()

        url = component.api_url_for('get_contributors_from_parent')
        res = self.app.get(url, auth=self.user.auth)
        # Should be all contributors, client-side handles marking
        # contributors that are already added to the child.

        ids = [contrib['id'] for contrib in res.json['contributors']]
        assert_not_in(user_already_on_component.id, ids)
        assert_equal(
            len(res.json['contributors']),
            2,
        )
