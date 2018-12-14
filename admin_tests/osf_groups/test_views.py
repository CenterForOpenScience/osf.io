from admin.osf_groups.views import (
    OSFGroupsView,
    OSFGroupsListView,
    OSFGroupsFormView
)
from admin_tests.utilities import setup_log_view
from nose import tools as nt
from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, ProjectFactory, OSFGroupFactory


class TestOSFGroupsView(AdminTestCase):

    def setUp(self):
        super(TestOSFGroupsView, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.group = OSFGroupFactory(name='', creator=self.user)
        self.group.add_group_to_node(self.project)
        self.group.save()
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = OSFGroupsView()
        view = setup_log_view(view, self.request, id=self.group.id)

        group = view.get_object()

        nt.assert_equal(self.group.name, group['name'])
        nt.assert_equal(self.group.creator, group['creator'])
        nt.assert_equal(list(self.group.members.all()), group['members'])
        nt.assert_equal(list(self.group.managers.all()), group['managers'])
        nt.assert_equal(list(self.group.nodes), group['nodes'])


class TestOSFGroupsListView(AdminTestCase):

    def setUp(self):
        super(TestOSFGroupsListView, self).setUp()
        self.user = UserFactory()
        self.group = OSFGroupFactory(name='Brian Dawkins', creator=self.user)
        self.group2 = OSFGroupFactory(name='Brian Westbrook', creator=self.user)
        self.group3 = OSFGroupFactory(name='Darren Sproles', creator=self.user)
        self.request = RequestFactory().post('/fake_path')
        self.view = OSFGroupsListView()

    def test_get_default_queryset(self):
        view = setup_log_view(self.view, self.request)

        queryset = view.get_queryset()

        nt.assert_equal(len(queryset), 3)

        nt.assert_in(self.group, queryset)
        nt.assert_in(self.group2, queryset)
        nt.assert_in(self.group3, queryset)

    def test_get_queryset_by_name(self):
        request = RequestFactory().post('/fake_path/?name=Brian')
        view = setup_log_view(self.view, request)

        queryset = view.get_queryset()

        nt.assert_equal(len(queryset), 2)

        nt.assert_in(self.group, queryset)
        nt.assert_in(self.group2, queryset)


class TestOSFGroupsFormView(AdminTestCase):

    def setUp(self):
        super(TestOSFGroupsFormView, self).setUp()
        self.user = UserFactory()
        self.group = OSFGroupFactory(name='Brian Dawkins', creator=self.user)
        self.group2 = OSFGroupFactory(name='Brian Westbrook', creator=self.user)
        self.view = OSFGroupsFormView()

    def test_post_id(self):
        request = RequestFactory().post('/fake_path', data={'id': self.group.id, 'name': ''})
        view = setup_log_view(self.view, request)

        redirect = view.post(request)
        assert redirect.url == '/osf_groups/{}/'.format(self.group._id)

    def test_post_name(self):
        request = RequestFactory().post('/fake_path', data={'id': '', 'name': 'Brian'})
        view = setup_log_view(self.view, request)

        redirect = view.post(request)
        assert redirect.url == '/osf_groups/?name=Brian'
