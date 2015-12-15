import unittest
from nose.tools import *  # PEP8 asserts

from website.project.model import AlternativeCitation

from modularodm.exceptions import ValidationError

from tests.base import OsfTestCase

from tests.factories import UserFactory, ProjectFactory

class ModelTests(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.citation = AlternativeCitation(name='Initial Citation', text='This is my test citation')
        self.citation.save()
        self.node.alternative_citations.append(self.citation)

    def test_model_success(self):
        alt_citation = AlternativeCitation(name='test', text='citation')
        alt_citation.save()
        self.node.alternative_citations.append(alt_citation)
        assert_equal(len(self.node.alternative_citations), 2)

    def test_model_no_name(self):
        alt_citation = AlternativeCitation(text='citation')
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.append(alt_citation)
        assert_equal(len(self.node.alternative_citations), 1)

    def test_model_no_text(self):
        alt_citation = AlternativeCitation(name='test')
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.append(alt_citation)
        assert_equal(len(self.node.alternative_citations), 1)

    def test_model_no_fields(self):
        alt_citation = AlternativeCitation()
        with assert_raises(ValidationError):
            alt_citation.save()
            self.node.alternative_citations.append(alt_citation)
        assert_equal(len(self.node.alternative_citations), 1)

    def test_model_change_name(self):
        citation = self.node.alternative_citations[0]
        citation.name = "New name"
        citation.save()
        self.node.save()
        assert_equal(self.node.alternative_citations[0].name, "New name")

    def test_model_change_text(self):
        citation = self.node.alternative_citations[0]
        citation.text = "New citation text"
        citation.save()
        self.node.save()
        assert_equal(self.node.alternative_citations[0].text, "New citation text")

if __name__ == '__main__':
    unittest.main()
