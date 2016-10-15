# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
from modularodm.exceptions import NoResultsFound, ValidationValueError

from tests.base import OsfTestCase
from tests.factories import SubjectFactory

from website.project.taxonomies import validate_subject_hierarchy


class TestSubjectValidation(OsfTestCase):
    def setUp(self):
        super(TestSubjectValidation, self).setUp()

        self.root_subject = SubjectFactory()
        self.one_level_root = SubjectFactory()
        self.two_level_root = SubjectFactory()
        self.outside_root = SubjectFactory()

        self.parent_subj_0 = SubjectFactory(parents=[self.root_subject])
        self.parent_subj_1 = SubjectFactory(parents=[self.root_subject])
        self.two_level_parent = SubjectFactory(parents=[self.two_level_root])

        self.outside_parent = SubjectFactory(parents=[self.outside_root])

        self.child_subj_00 = SubjectFactory(parents=[self.parent_subj_0])
        self.child_subj_01 = SubjectFactory(parents=[self.parent_subj_0])
        self.child_subj_10 = SubjectFactory(parents=[self.parent_subj_1])
        self.child_subj_11 = SubjectFactory(parents=[self.parent_subj_1])
        self.outside_child = SubjectFactory(parents=[self.outside_parent])

        self.parent_subj_0.children = [self.child_subj_00, self.child_subj_01]
        self.parent_subj_1.children = [self.child_subj_10, self.child_subj_11]
        self.outside_parent.children = [self.outside_child]

        self.root_subject.children = [self.parent_subj_0, self.parent_subj_1]
        self.outside_root.children = [self.outside_parent]
        self.two_level_root.children = [self.two_level_parent]

        self.child_subj_00.save()
        self.child_subj_01.save()
        self.child_subj_10.save()
        self.child_subj_11.save()
        self.outside_child.save()

        self.parent_subj_0.save()
        self.parent_subj_1.save()
        self.outside_parent.save()
        self.two_level_parent.save()

        self.root_subject.save()
        self.outside_root.save()
        self.two_level_root.save()
        self.one_level_root.save()

        self.valid_full_hierarchy = [self.root_subject._id, self.parent_subj_0._id, self.child_subj_00._id]
        self.valid_two_level_hierarchy = [self.two_level_root._id, self.two_level_parent._id]
        self.valid_one_level_hierarchy = [self.one_level_root._id]
        self.valid_partial_hierarchy = [self.root_subject._id, self.parent_subj_1._id]
        self.valid_root = [self.root_subject._id]

        self.no_root = [self.parent_subj_0._id, self.child_subj_00._id]
        self.no_parent = [self.root_subject._id, self.child_subj_00._id]
        self.invalid_child_leaf = [self.root_subject._id, self.parent_subj_0._id, self.child_subj_10._id]
        self.invalid_parent_leaf = [self.root_subject._id, self.outside_parent._id, self.child_subj_00._id]
        self.invalid_root_leaf = [self.outside_root._id, self.parent_subj_0._id, self.child_subj_00._id]
        self.invalid_ids = ['notarealsubjectid', 'thisisalsoafakeid']

    def test_validation_full_hierarchy(self):
        assert_equal(validate_subject_hierarchy(self.valid_full_hierarchy), None)

    def test_validation_two_level_hierarchy(self):
        assert_equal(validate_subject_hierarchy(self.valid_two_level_hierarchy), None)

    def test_validation_one_level_hierarchy(self):
        assert_equal(validate_subject_hierarchy(self.valid_one_level_hierarchy), None)

    def test_validation_partial_hierarchy(self):
        assert_equal(validate_subject_hierarchy(self.valid_partial_hierarchy), None)

    def test_validation_root_only(self):
        assert_equal(validate_subject_hierarchy(self.valid_root), None)

    def test_invalidation_no_root(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.no_root)

        assert_in('Unable to find root', e.exception.message)

    def test_invalidation_no_parent(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.no_parent)

        assert_in('Invalid subject hierarchy', e.exception.message)

    def test_invalidation_invalid_child_leaf(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.invalid_child_leaf)

        assert_in('Invalid subject hierarchy', e.exception.message)

    def test_invalidation_invalid_parent_leaf(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.invalid_parent_leaf)

        assert_in('Invalid subject hierarchy', e.exception.message)

    def test_invalidation_invalid_root_leaf(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.invalid_root_leaf)

        assert_in('Invalid subject hierarchy', e.exception.message)

    def test_invalidation_invalid_ids(self):
        with assert_raises(ValidationValueError) as e:
            validate_subject_hierarchy(self.invalid_ids)

        assert_in('could not be found', e.exception.message)
