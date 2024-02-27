"""Tests related to project decorators"""

from website.project.decorators import must_be_valid_project

from osf.models import Sanction

from tests.base import OsfTestCase
from osf_tests.factories import ProjectFactory, NodeFactory, RetractionFactory, CollectionFactory, RegistrationFactory

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
        super().setUp()
        self.project = ProjectFactory()
        self.node = NodeFactory()
        self.auth = Auth(user=self.project.creator)

    def test_populates_kwargs_node(self):
        res = valid_project_helper(pid=self.project._id)
        self.assertEqual(res['node'], self.project)
        self.assertIsNone(res['parent'])

    def test_populates_kwargs_node_and_parent(self):
        res = valid_project_helper(pid=self.project._id, nid=self.node._id)
        self.assertEqual(res['parent'], self.project)
        self.assertEqual(res['node'], self.node)

    def test_project_not_found(self):
        with self.assertRaises(HTTPError) as exc_info:
            valid_project_helper(pid='fakepid')
        self.assertEqual(exc_info.exception.code, 404)

    def test_project_deleted(self):
        self.project.is_deleted = True
        self.project.save()
        with self.assertRaises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id)
        self.assertEqual(exc_info.exception.code, 410)

    def test_node_not_found(self):
        with self.assertRaises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid='fakenid')
        self.assertEqual(exc_info.exception.code, 404)

    def test_node_deleted(self):
        self.node.is_deleted = True
        self.node.save()
        with self.assertRaises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid=self.node._id)
        self.assertEqual(exc_info.exception.code, 410)

    def test_valid_project_as_factory_allow_retractions_is_retracted(self):
        registration = RegistrationFactory(project=self.project)
        registration.retraction = RetractionFactory()
        registration.retraction.state = Sanction.UNAPPROVED
        registration.retraction.save()
        res = as_factory_allow_retractions(pid=registration._id)
        self.assertEqual(res['node'], registration)

    def test_collection_guid_not_found(self):
        collection = CollectionFactory()
        collection.collect_object(self.project, self.auth.user)
        with self.assertRaises(HTTPError) as exc_info:
            valid_project_helper(pid=collection._id, nid=collection._id)
        self.assertEqual(exc_info.exception.code, 404)
