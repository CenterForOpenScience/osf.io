from nose import tools as nt
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, SubjectFactory
from admin.subjects.views import SubjectListView, SubjectUpdateView


class TestSubjectListView(AdminTestCase):

    def setUp(self):
        self.subject = SubjectFactory()
        self.plain_view = SubjectListView
        self.url = reverse('subjects:list')

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(self.url)
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.plain_view.as_view()(request)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()

        view_permission = Permission.objects.get(codename='view_subject')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request)
        nt.assert_equal(response.status_code, 200)


class TestSubjectUpdateView(AdminTestCase):

    def setUp(self):
        self.subject = SubjectFactory()
        self.plain_view = SubjectUpdateView
        self.url = reverse('subjects:update', kwargs={'pk': self.subject.pk})

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(self.url)
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.plain_view.as_view()(request, pk=self.subject.pk)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        edit_permission = Permission.objects.get(codename='change_subject')
        user.user_permissions.add(edit_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, pk=self.subject.pk)
        nt.assert_equal(response.status_code, 200)
