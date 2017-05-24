import pytest

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)

@pytest.mark.django_db
class NodeCitationsMixin:

	def setUp(self):
		self.app = JSONAPITestApp()
		self.admin_contributor = AuthUserFactory()
		self.rw_contributor = AuthUserFactory()
		self.read_contributor = AuthUserFactory()
		self.non_contributor = AuthUserFactory()

		self.public_project = ProjectFactory(creator=self.admin_contributor, is_public=True)

		self.private_project = ProjectFactory(creator=self.admin_contributor)
		self.private_project.add_contributor(self.rw_contributor, auth=Auth(self.admin_contributor))
		self.private_project.add_contributor(self.read_contributor, permissions=['read'], auth=Auth(self.admin_contributor))
		self.private_project.save()

	def test_node_citations(self):

	#   test_admin_can_view_private_project_citations
		res = self.app.get(self.private_url, auth=self.admin_contributor.auth)
		assert res.status_code == 200

	#   test_rw_contributor_can_view_private_project_citations
		res = self.app.get(self.private_url, auth=self.rw_contributor.auth)
		assert res.status_code == 200

	#   test_read_contributor_can_view_private_project_citations
		res = self.app.get(self.private_url, auth=self.read_contributor.auth)
		assert res.status_code == 200

	#   test_non_contributor_cannot_view_private_project_citations
		res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
		assert res.status_code == 403
		assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

	#   test_unauthenticated_cannot_view_private_project_citations
		res = self.app.get(self.private_url, expect_errors=True)
		assert res.status_code == 401
		assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

	#   test_unauthenticated_can_view_public_project_citations
		res = self.app.get(self.public_url)
		assert res.status_code == 200

	#   test_citations_are_read_only
		post_res = self.app.post_json_api(self.public_url, {}, auth=self.admin_contributor.auth, expect_errors=True)
		assert post_res.status_code == 405
		put_res = self.app.put_json_api(self.public_url, {}, auth=self.admin_contributor.auth, expect_errors=True)
		assert put_res.status_code == 405
		delete_res = self.app.delete_json_api(self.public_url, auth=self.admin_contributor.auth, expect_errors=True)
		assert delete_res.status_code == 405


class TestNodeCitations(NodeCitationsMixin):

	@pytest.fixture(autouse=True)
	def setUp(self):
		super(TestNodeCitations, self).setUp()
		self.public_url = '/{}nodes/{}/citation/'.format(API_BASE, self.public_project._id)
		self.private_url = '/{}nodes/{}/citation/'.format(API_BASE, self.private_project._id)


class TestNodeCitationsStyle(NodeCitationsMixin):

	@pytest.fixture(autouse=True)
	def setUp(self):
		super(TestNodeCitationsStyle, self).setUp()
		self.public_url = '/{}nodes/{}/citation/apa/'.format(API_BASE, self.public_project._id)
		self.private_url = '/{}nodes/{}/citation/apa/'.format(API_BASE, self.private_project._id)
