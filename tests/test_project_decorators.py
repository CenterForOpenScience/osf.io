"""Tests related to project decorators"""

from nose.tools import *  # noqa

from website.project.decorators import must_be_valid_project

from website.project.model import Sanction

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, NodeFactory, RetractionFactory, CollectionFactory

from framework.exceptions import HTTPError
from framework.auth import Auth


@must_be_valid_project
def valid_project_helper(**kwargs):
    return kwargs

@must_be_valid_project(retractions_valid=True)
def as_factory_allow_retractions(**kwargs):
    return kwargs


class TestValidProject(OsfTestCase):

    def setUp(self):
        super(TestValidProject, self).setUp()
        self.project = ProjectFactory()
        self.node = NodeFactory(project=self.project)
        self.retraction = RetractionFactory()
        self.auth = Auth(user=self.project.creator)

    def test_populates_kwargs_node(self):
        res = valid_project_helper(pid=self.project._id)
        assert_equal(res['node'], self.project)
        assert_is_none(res['parent'])

    def test_populates_kwargs_node_and_parent(self):
        res = valid_project_helper(pid=self.project._id, nid=self.node._id)
        assert_equal(res['parent'], self.project)
        assert_equal(res['node'], self.node)

    def test_project_not_found(self):
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid='fakepid')
        assert_equal(exc_info.exception.code, 404)

    def test_project_deleted(self):
        self.project.is_deleted = True
        self.project.save()
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id)
        assert_equal(exc_info.exception.code, 410)

    def test_node_not_found(self):
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid='fakenid')
        assert_equal(exc_info.exception.code, 404)

    def test_node_deleted(self):
        self.node.is_deleted = True
        self.node.save()
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid=self.node._id)
        assert_equal(exc_info.exception.code, 410)

    def test_valid_project_as_factory_allow_retractions_is_retracted(self):
        self.project.is_registration = True
        self.project.retraction = self.retraction
        self.retraction.state = Sanction.UNAPPROVED
        self.retraction.save()
        res = as_factory_allow_retractions(pid=self.project._id)
        assert_equal(res['node'], self.project)

    def test_collection_guid_bad_request(self):
        collection = CollectionFactory()
        collection.add_pointer(self.project, self.auth)
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=collection._id, nid=collection._id)
        assert_equal(exc_info.exception.code, 400)
