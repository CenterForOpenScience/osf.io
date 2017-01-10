# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


class NodeCitationsMixin(object):

	def setUp(self):
		super(NodeCitationsMixin, self).setUp()

		self.admin_contributor = AuthUserFactory()
		self.rw_contributor = AuthUserFactory()
		self.read_contributor = AuthUserFactory()
		self.non_contributor = AuthUserFactory()

		self.public_project = ProjectFactory(creator=self.admin_contributor, is_public=True)

		self.private_project = ProjectFactory(creator=self.admin_contributor)
		self.private_project.add_contributor(self.rw_contributor, auth=Auth(self.admin_contributor))
		self.private_project.add_contributor(self.read_contributor, permissions=['read'], auth=Auth(self.admin_contributor))
		self.private_project.save()

	def test_admin_can_view_private_project_citations(self):
		res = self.app.get(self.private_url, auth=self.admin_contributor.auth)
		assert_equal(res.status_code, 200)

	def test_rw_contributor_can_view_private_project_citations(self):
		res = self.app.get(self.private_url, auth=self.rw_contributor.auth)
		assert_equal(res.status_code, 200)

	def test_read_contributor_can_view_private_project_citations(self):
		res = self.app.get(self.private_url, auth=self.read_contributor.auth)
		assert_equal(res.status_code, 200)

	def test_non_contributor_cannot_view_private_project_citations(self):
		res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
		assert_equal(res.status_code, 403)
		assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

	def test_unauthenticated_cannot_view_private_project_citations(self):
		res = self.app.get(self.private_url, expect_errors=True)
		assert_equal(res.status_code, 401)
		assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

	def test_unauthenticated_can_view_public_project_citations(self):
		res = self.app.get(self.public_url)
		assert_equal(res.status_code, 200)

	def test_citations_are_read_only(self):
		post_res = self.app.post_json_api(self.public_url, {}, auth=self.admin_contributor.auth, expect_errors=True)
		assert_equal(post_res.status_code, 405)
		put_res = self.app.put_json_api(self.public_url, {}, auth=self.admin_contributor.auth, expect_errors=True)
		assert_equal(put_res.status_code, 405)
		delete_res = self.app.delete_json_api(self.public_url, auth=self.admin_contributor.auth, expect_errors=True)
		assert_equal(delete_res.status_code, 405)


class TestNodeCitations(NodeCitationsMixin, ApiTestCase):

	def setUp(self):
		super(TestNodeCitations, self).setUp()
		self.public_url = '/{}nodes/{}/citation/'.format(API_BASE, self.public_project._id)
		self.private_url = '/{}nodes/{}/citation/'.format(API_BASE, self.private_project._id)


class TestNodeCitationsStyle(NodeCitationsMixin, ApiTestCase):

	def setUp(self):
		super(TestNodeCitationsStyle, self).setUp()
		self.public_url = '/{}nodes/{}/citation/apa/'.format(API_BASE, self.public_project._id)
		self.private_url = '/{}nodes/{}/citation/apa/'.format(API_BASE, self.private_project._id)
