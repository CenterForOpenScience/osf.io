from admin.osf_groups.views import (
    OSFGroupsListView,
    OSFGroupsFormView
)
from admin_tests.utilities import setup_log_view
from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, OSFGroupFactory


class TestOSFGroupsListView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.group = OSFGroupFactory(name='Brian Dawkins', creator=self.user)
        self.group2 = OSFGroupFactory(name='Brian Westbrook', creator=self.user)
        self.group3 = OSFGroupFactory(name='Darren Sproles', creator=self.user)
        self.request = RequestFactory().post('/fake_path')
        self.view = OSFGroupsListView()

    def test_get_default_queryset(self):
        view = setup_log_view(self.view, self.request)

        queryset = view.get_queryset()

        assert len(queryset) == 3

        assert self.group in queryset
        assert self.group2 in queryset
        assert self.group3 in queryset

    def test_get_queryset_by_name(self):
        request = RequestFactory().post('/fake_path/?name=Brian')
        view = setup_log_view(self.view, request)

        queryset = view.get_queryset()

        assert len(queryset) == 2

        assert self.group in queryset
        assert self.group2 in queryset


class TestOSFGroupsFormView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.group = OSFGroupFactory(name='Brian Dawkins', creator=self.user)
        self.group2 = OSFGroupFactory(name='Brian Westbrook', creator=self.user)
        self.view = OSFGroupsFormView()

    def test_post_id(self):
        request = RequestFactory().post('/fake_path', data={'id': self.group._id, 'name': ''})
        view = setup_log_view(self.view, request)

        redirect = view.post(request)
        assert redirect.url == f'/osf_groups/{self.group._id}/'

    def test_post_name(self):
        request = RequestFactory().post('/fake_path', data={'id': '', 'name': 'Brian'})
        view = setup_log_view(self.view, request)

        redirect = view.post(request)
        assert redirect.url == '/osf_groups/?name=Brian'
