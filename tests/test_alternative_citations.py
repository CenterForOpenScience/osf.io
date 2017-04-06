import unittest
from nose.tools import *  # flake8: noqa (PEP8 asserts)

from framework.auth.core import Auth

from website.project.model import AlternativeCitation

from modularodm.exceptions import ValidationError

from tests.base import OsfTestCase

from osf_tests.factories import UserFactory, ProjectFactory

class ModelTests(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.citation = AlternativeCitation(name='name', text='text')
        self.citation.save()
        self.node.alternative_citations.add(self.citation)

    def test_model_success(self):
        alt_citation = AlternativeCitation(name='test', text='citation')
        alt_citation.save()
        self.node.alternative_citations.add(alt_citation)
        assert_equal(self.node.alternative_citations.count(), 2)

    def test_model_no_name(self):
        alt_citation = AlternativeCitation(text='citation')
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.add(alt_citation)
        assert_equal(self.node.alternative_citations.count(), 1)

    def test_model_no_text(self):
        alt_citation = AlternativeCitation(name='test')
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.add(alt_citation)
        assert_equal(self.node.alternative_citations.count(), 1)

    def test_model_no_fields(self):
        alt_citation = AlternativeCitation()
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.add(alt_citation)
        assert_equal(self.node.alternative_citations.count(), 1)

    def test_model_change_name(self):
        citation = self.node.alternative_citations.first()
        citation.name = 'New name'
        citation.save()
        self.node.save()
        assert_equal(self.node.alternative_citations.first().name, 'New name')

    def test_model_change_text(self):
        citation = self.node.alternative_citations.first()
        citation.text = 'New citation text'
        citation.save()
        self.node.save()
        assert_equal(self.node.alternative_citations.first().text, 'New citation text')

    def test_model_fork(self):
        fork = self.node.fork_node(auth=Auth(self.user))
        assert_equal(self.node.alternative_citations.count(), fork.alternative_citations.count(), 1)
        assert_equal(self.node.alternative_citations.first().name, fork.alternative_citations.first().name, 'name')
        assert_equal(self.node.alternative_citations.first().text, fork.alternative_citations.first().text, 'text')
        assert_not_equal(self.node.alternative_citations.first()._id, fork.alternative_citations.first()._id)

    def test_model_fork_change_name(self):
        fork = self.node.fork_node(auth=Auth(self.user))
        assert_equal(self.node.alternative_citations.count(), fork.alternative_citations.count(), 1)
        alt_citation = fork.alternative_citations.first()
        alt_citation.name = 'new name'
        alt_citation.save()
        assert_not_equal(self.node.alternative_citations.first().name, fork.alternative_citations.first().name)
        assert_equal(self.node.alternative_citations.first().text, fork.alternative_citations.first().text, 'text')
        assert_not_equal(self.node.alternative_citations.first()._id, fork.alternative_citations.first()._id)

    def test_model_fork_change_text(self):
        fork = self.node.fork_node(auth=Auth(self.user))
        assert_equal(self.node.alternative_citations.count(), fork.alternative_citations.count(), 1)
        alt_citation = fork.alternative_citations.first()
        alt_citation.text = 'new text'
        alt_citation.save()
        assert_not_equal(self.node.alternative_citations.first().text, fork.alternative_citations.first().text)
        assert_equal(self.node.alternative_citations.first().name, fork.alternative_citations.first().name, 'name')
        assert_not_equal(self.node.alternative_citations.first()._id, fork.alternative_citations.first()._id)

if __name__ == '__main__':
    unittest.main()
