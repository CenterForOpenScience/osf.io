from nose.tools import *  # flake8: noqa

from django.db.models import Q

from tests.base import AdminTestCase

from osf_tests.factories import SubjectFactory

from osf.models import Subject
from osf.models.preprint_provider import rules_to_subjects
from admin.base.utils import get_subject_rules


import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TestSubjectRules(AdminTestCase):

    def setUp(self):
        super(TestSubjectRules, self).setUp()

        self.parent_one = SubjectFactory()  # 0
        self.parent_two = SubjectFactory()  # 1

        self.child_one_1 = SubjectFactory(parent=self.parent_one)  # 2
        self.child_one_2 = SubjectFactory(parent=self.parent_one)  # 3
        self.grandchild_one_1 = SubjectFactory(parent=self.child_one_1)  # 4
        self.grandchild_one_2 = SubjectFactory(parent=self.child_one_1)  # 5

        self.child_two_1 = SubjectFactory(parent=self.parent_two)  # 6
        self.child_two_2 = SubjectFactory(parent=self.parent_two)  # 7

    def test_error_when_child_called_without_parent(self):
        subjects_selected = [self.child_one_1]

        with self.assertRaises(AttributeError):
            get_subject_rules(subjects_selected)

    def test_just_toplevel_subject(self):
        subjects_selected = [self.parent_one]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [[[self.parent_one._id], False]]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_two_toplevel_subjects(self):
        subjects_selected = [
            self.parent_one,
            self.parent_two
        ]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [
            [[self.parent_one._id], False],
            [[self.parent_two._id], False]
        ]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_one_child(self):
        subjects_selected = [
            self.parent_one,
            self.child_one_1
        ]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [[[self.parent_one._id, self.child_one_1._id], False]]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_one_child_all_grandchildren(self):
        subjects_selected = [
            self.parent_one,
            self.child_one_1,
            self.grandchild_one_1,
            self.grandchild_one_2,
        ]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [[[self.parent_one._id, self.child_one_1._id], True]]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_all_children_all_grandchildren(self):
        subjects_selected = [
            self.parent_one,
            self.child_one_1,
            self.grandchild_one_1,
            self.grandchild_one_2,
            self.child_one_2
        ]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [[[self.parent_one._id], True]]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_one_child_with_one_grandchild(self):
        subjects_selected = [
            self.parent_one,
            self.child_one_1,
            self.grandchild_one_1
        ]
        rules_returned = get_subject_rules(subjects_selected)
        rules_ideal = [
            [[self.parent_one._id, self.child_one_1._id, self.grandchild_one_1._id], False]
        ]
        self.assertItemsEqual(rules_returned, rules_ideal)

    def test_rules_to_subjects(self):
        rules = [
            [[self.parent_one._id, self.child_one_1._id], False]
        ]
        subject_queryset_ideal = Subject.objects.filter(Q(id=self.parent_one.id) | Q(id=self.child_one_1.id))
        returned_subjects = rules_to_subjects(rules)

        self.assertItemsEqual(subject_queryset_ideal, returned_subjects)
