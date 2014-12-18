# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts

from tests.factories import ProjectFactory, NodeFactory, AuthUserFactory
from tests.base import OsfTestCase, fake

from framework.auth.decorators import Auth


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
        # Should be one contributor to the parent who is both visible and
        # not a contributor on the component
        assert_equal(
            len(res.json['contributors']),
            1,
        )

    def test_get_most_in_common_contributors(self):
        # project 1 (contrib 1, contrib 2, unreg_contrib 3)
        #  - component 1 (contrib 1)
        # project 2 - add should show contrib 1 first (2 links), contrib 2 second (1 link)
        contributor_1 = AuthUserFactory()
        contributor_2 = AuthUserFactory()
        self.project.add_contributor(contributor_1, auth=self.auth)
        self.project.add_contributor(contributor_2, auth=self.auth)
        # has one unregistered contributor
        self.project.add_unregistered_contributor(
            fullname=fake.name(),
            email=fake.email(),
            auth=self.auth,
        )
        self.project.save()
        component = NodeFactory(parent=self.project, creator=self.user)
        component.add_contributor(contributor_1, auth=self.auth)
        component.save()
        project_2 = ProjectFactory(creator=self.user)
        project_2.add_contributor(contributor_1, auth=self.auth)
        url = project_2.api_url_for('get_most_in_common_contributors')
        res = self.app.get(url, auth=self.user.auth)
        project_2.reload()
        res_contribs = res.json['contributors']
        assert_equal(len(res.json['contributors']), 2)
        assert_equal(contributor_1._id, res_contribs[0]['id'])
        assert_equal(res_contribs[0]['n_projects_in_common'], 2)
        assert_equal(contributor_2._id, res_contribs[1]['id'])
        assert_equal(res_contribs[1]['n_projects_in_common'], 1)

    def test_get_recently_added_contributors(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(AuthUserFactory(), auth=self.auth)
        project.add_contributor(AuthUserFactory(), auth=self.auth)
        # has one unregistered contributor
        project.add_unregistered_contributor(
            fullname=fake.name(),
            email=fake.email(),
            auth=self.auth,
        )
        project.save()
        url = self.project.api_url_for('get_recently_added_contributors')
        res = self.app.get(url, auth=self.user.auth)
        project.reload()
        recent = [c for c in self.user.recently_added if c.is_active]
        assert_equal(len(res.json['contributors']), len(recent))


    def test_get_recently_added_contributors_with_limit(self):
        project = ProjectFactory(creator=self.user)
        for _ in range(5):
            project.add_contributor(AuthUserFactory(), auth=self.auth)
        project.save()
        url = self.project.api_url_for('get_recently_added_contributors', max=4)
        res = self.app.get(url, auth=self.user.auth)
        project.reload()
        assert_equal(len(res.json['contributors']), 4)
