# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from nose.tools import *  # flake8: noqa (PEP8 asserts)
from osf.exceptions import ValidationValueError

from tests.base import OsfTestCase
from osf_tests.factories import SubjectFactory, PreprintFactory, PreprintProviderFactory

from osf.models.validators import validate_subject_hierarchy


class TestSubjectTreeValidation(OsfTestCase):
    def setUp(self):
        super(TestSubjectTreeValidation, self).setUp()

        self.root_subject = SubjectFactory()
        self.one_level_root = SubjectFactory()
        self.two_level_root = SubjectFactory()
        self.outside_root = SubjectFactory()

        self.root_subject.save()
        self.outside_root.save()
        self.two_level_root.save()
        self.one_level_root.save()

        self.parent_subj_0 = SubjectFactory(parent=self.root_subject)
        self.parent_subj_1 = SubjectFactory(parent=self.root_subject)
        self.two_level_parent = SubjectFactory(parent=self.two_level_root)

        self.outside_parent = SubjectFactory(parent=self.outside_root)

        self.parent_subj_0.save()
        self.parent_subj_1.save()
        self.outside_parent.save()
        self.two_level_parent.save()

        self.child_subj_00 = SubjectFactory(parent=self.parent_subj_0)
        self.child_subj_01 = SubjectFactory(parent=self.parent_subj_0)
        self.child_subj_10 = SubjectFactory(parent=self.parent_subj_1)
        self.child_subj_11 = SubjectFactory(parent=self.parent_subj_1)
        self.outside_child = SubjectFactory(parent=self.outside_parent)

        self.child_subj_00.save()
        self.child_subj_01.save()
        self.child_subj_10.save()
        self.child_subj_11.save()
        self.outside_child.save()

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

    def test_hiarachy_property(self):
        assert_equal(self.child_subj_00.hierarchy, [self.root_subject._id, self.parent_subj_0._id, self.child_subj_00._id])
        assert_equal(self.two_level_parent.hierarchy, [self.two_level_root._id, self.two_level_parent._id])
        assert_equal(self.one_level_root.hierarchy, [self.one_level_root._id])
        assert_equal(self.parent_subj_1.hierarchy, [self.root_subject._id, self.parent_subj_1._id])
        assert_equal(self.root_subject.hierarchy, [self.root_subject._id])


    def test_object_hierarchy_property(self):
        assert_equal(self.child_subj_00.object_hierarchy, [self.root_subject, self.parent_subj_0, self.child_subj_00])
        assert_equal(self.two_level_parent.object_hierarchy, [self.two_level_root, self.two_level_parent])
        assert_equal(self.one_level_root.object_hierarchy, [self.one_level_root])
        assert_equal(self.parent_subj_1.object_hierarchy, [self.root_subject, self.parent_subj_1])
        assert_equal(self.root_subject.object_hierarchy, [self.root_subject])

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

class TestSubjectEditValidation(OsfTestCase):
    def setUp(self):
        super(TestSubjectEditValidation, self).setUp()
        self.subject = SubjectFactory()

    def test_edit_unused_subject(self):
        self.subject.text = 'asdfg'
        self.subject.save()

    def test_edit_used_subject(self):
        preprint = PreprintFactory(subjects=[[self.subject._id]])
        self.subject.text = 'asdfg'
        with assert_raises(ValidationError):
            self.subject.save()

    def test_delete_unused_subject(self):
        self.subject.delete()

    def test_delete_used_subject(self):
        preprint = PreprintFactory(subjects=[[self.subject._id]])
        with assert_raises(ValidationError):
            self.subject.delete()

    def test_max_highlighted_count(self):
        highlights = [SubjectFactory(provider=self.subject.provider, highlighted=True) for _ in range(10)]
        with assert_raises(ValidationError):
            self.subject.highlighted=True
            self.subject.save()

class TestSubjectProperties(OsfTestCase):
    def setUp(self):
        super(TestSubjectProperties, self).setUp()

        self.osf_provider = PreprintProviderFactory(_id='osf', share_title='bepress')
        self.asdf_provider = PreprintProviderFactory(_id='asdf')
        self.bepress_subj = SubjectFactory(text='BePress Text', provider=self.osf_provider)
        self.other_subj = SubjectFactory(text='Other Text', bepress_subject=self.bepress_subj, provider=self.asdf_provider)

    def test_bepress_text(self):
        assert self.other_subj.bepress_text == 'BePress Text'
        assert self.bepress_subj.bepress_text == 'BePress Text'

    def test_path(self):
        self.bepress_child = SubjectFactory(text='BePress Child', provider=self.osf_provider, parent=self.bepress_subj)
        self.other_child = SubjectFactory(text='Other Child', bepress_subject=self.bepress_subj, provider=self.asdf_provider, parent=self.other_subj)

        assert self.bepress_subj.path == 'bepress|BePress Text'
        assert self.bepress_child.path == 'bepress|BePress Text|BePress Child'
        assert self.other_subj.path == 'asdf|Other Text'
        assert self.other_child.path == 'asdf|Other Text|Other Child'
