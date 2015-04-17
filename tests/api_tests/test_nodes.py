# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from website.models import Node
from website.util import api_v2_url_for
from tests.base import OsfTestCase, fake
from tests.factories import UserFactory, ProjectFactory


class TestNodeList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.auth = (self.user.username, 'justapoorboy')

    def test_returns_200(self):
        res = self.app.get('/api/v2/nodes/')
        assert_equal(res.status_code, 200)

    def test_only_returns_non_deleted_public_projects(self):
        deleted = ProjectFactory(is_deleted=True)
        private = ProjectFactory(is_public=False)
        public = ProjectFactory(is_public=True)

        res = self.app.get('/api/v2/nodes/')
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert_in(public._id, ids)
        assert_not_in(deleted._id, ids)
        assert_not_in(private._id, ids)

        Node.remove()

# FIXME: These tests show different results when run in isolation vs. full suite
# I believe this is because api_v2_url_for behaves differently depending on
# app initialization state. May need to subclass Django's test case?
class TestNodeContributorList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()

        password = fake.password()
        self.password = password

        self.user.set_password(password)
        self.user.save()
        self.auth = (self.user.username, password)

        self.project = ProjectFactory(is_public=False)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_must_be_contributor(self):

        non_contrib = UserFactory.build()
        pw = fake.password()
        non_contrib.set_password(pw)
        non_contrib.save()

        url = api_v2_url_for('nodes:node-contributors', kwargs=dict(pk=self.project._id))
        # non-authenticated
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # non-contrib
        res = self.app.get(url, auth=(non_contrib.username, pw), expect_errors=True)
        assert_equal(res.status_code, 401)

        # contrib
        res = self.app.get(url, auth=(self.user.username, self.password))
        assert_equal(res.status_code, 200)
        Node.remove()
