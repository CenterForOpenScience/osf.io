from nose.tools import *  # noqa: F403
import pytest
import datetime as datetime

from django.test import RequestFactory
from django.db.models import Q
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.admin.sites import AdminSite

from tests.base import AdminTestCase

from osf_tests.factories import SubjectFactory, UserFactory, RegistrationFactory, PreprintFactory

from osf.models import Subject, OSFUser
from osf.models.provider import rules_to_subjects
from admin.base.utils import get_subject_rules, change_embargo_date
from osf.admin import OSFUserAdmin


import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MockRequest:
    pass


request = MockRequest()
site = AdminSite()


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

class TestNodeChanges(AdminTestCase):
    def setUp(self):
        super(TestNodeChanges, self).setUp()
        self.registration = RegistrationFactory(is_public=True)
        self.user = UserFactory()
        self.user.is_staff = True
        self.user.groups.add(Group.objects.get(name='osf_admin'))
        self.user.save()

        self.date_valid = self.registration.registered_date + datetime.timedelta(days=365)
        self.date_valid2 = self.registration.registered_date + datetime.timedelta(days=375)
        self.date_too_late = self.registration.registered_date + datetime.timedelta(days=1825)
        self.date_too_soon = self.registration.registered_date + datetime.timedelta(days=-1)

    def test_change_embargo_date(self):

        assert_false(self.registration.embargo)
        assert_true(self.registration.is_public)

        # Note: Date comparisons accept a difference up to a day because embargoes start at midnight

        # Create an embargo from a registration with none
        change_embargo_date(self.registration, self.user, self.date_valid)
        assert_almost_equal(self.registration.embargo.end_date, self.date_valid, delta=datetime.timedelta(days=1))

        # Make sure once embargo is set, registration is made private
        self.registration.reload()
        assert_false(self.registration.is_public)

        # Update an embargo end date
        change_embargo_date(self.registration, self.user, self.date_valid2)
        assert_almost_equal(self.registration.embargo.end_date, self.date_valid2, delta=datetime.timedelta(days=1))

        # Test invalid dates
        with assert_raises(ValidationError):
            change_embargo_date(self.registration, self.user, self.date_too_late)
        with assert_raises(ValidationError):
            change_embargo_date(self.registration, self.user, self.date_too_soon)

        # Test that checks user has permission
        with assert_raises(PermissionDenied):
            change_embargo_date(self.registration, UserFactory(), self.date_valid)

        assert_almost_equal(self.registration.embargo.end_date, self.date_valid2, delta=datetime.timedelta(days=1))

        # Add a test to check privatizing


class TestGroupCollectionsPreprints(AdminTestCase):

    @pytest.mark.enable_bookmark_creation
    def test_admin_app_groups(self):
        user = UserFactory()
        user.save()
        request = RequestFactory()
        get_request = request.get('/admin/osf/osfuser/{}/change'.format(user.id))
        get_request.user = user
        post_request = request.post('/admin/osf/osfuser/{}/change'.format(user.id))
        post_request.user = user
        preprint = PreprintFactory(creator=user)
        preprint.save()
        admin = OSFUserAdmin(OSFUser, site)
        formfield = (admin.formfield_for_manytomany(OSFUser.groups.field, request=get_request))
        queryset = formfield.queryset

        collections_group = Group.objects.filter(name__startswith='collections_')[0]
        assert(collections_group not in queryset)

        preprint_group = Group.objects.filter(name__startswith='preprint_')[0]
        assert(preprint_group not in queryset)

        form = admin.get_form(request=get_request, obj=user)
        get_form = form(get_request.GET, instance=user)
        post_request.POST = get_form
        #form = admin.get_form(request=post_request, obj=user)
        post_form = form(post_request.POST, instance=user)
        post_form.is_valid()
        assert(post_form.is_valid())
        post_form.save(commit=False)
        admin.save_related(request=post_request, form=post_form, formsets=[], change=True)
        assert(len(list(user.groups.filter(name__startswith='collections_'))) > 0)
        assert(len(list(user.groups.filter(name__startswith='preprint_'))) > 0)
