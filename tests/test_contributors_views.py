# -*- coding: utf-8 -*-

from nose.tools import *  # noqa; PEP8 asserts

from tests.factories import ProjectFactory, NodeFactory, AuthUserFactory
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
        self.project.save()
        component = NodeFactory(parent=self.project, creator=self.user)
        url = component.api_url_for('get_contributors_from_parent')
        res = self.app.get(url, auth=self.user.auth)
        # Should be all contributors, client-side handles marking
        # contributors that are already added to the child.
        assert_equal(
            len(res.json['contributors']),
            2,
        )
