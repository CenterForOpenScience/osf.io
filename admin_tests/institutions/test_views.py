import json

from nose import tools as nt
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied


from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory
)
from osf.models import Institution, Node

from admin_tests.utilities import setup_form_view, setup_user_view

from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm


class TestInstitutionList(AdminTestCase):
    def setUp(self):
        super(TestInstitutionList, self).setUp()

        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user = AuthUserFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionList()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_get_list(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_queryset(self):
        institutions_returned = list(self.view.get_queryset())
        inst_list = [self.institution1, self.institution2]
        nt.assert_equals(set(institutions_returned), set(inst_list))
        nt.assert_is_instance(institutions_returned[0], Institution)

    def test_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(len(res['institutions']), 2)
        nt.assert_is_instance(res['institutions'][0], Institution)


class TestInstitutionDisplay(AdminTestCase):
    def setUp(self):
        super(TestInstitutionDisplay, self).setUp()

        self.user = AuthUserFactory()

        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionDisplay()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, Institution)
        nt.assert_equal(obj.name, self.institution.name)

    def test_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['institution'], dict)
        nt.assert_equal(res['institution']['name'], self.institution.name)
        nt.assert_is_instance(res['change_form'], InstitutionForm)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)


class TestInstitutionDelete(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.DeleteInstitution()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_unaffiliated_institution_delete(self):
        redirect = self.view.delete(self.request)
        nt.assert_equal(redirect.url, '/institutions/')
        nt.assert_equal(redirect.status_code, 302)

    def test_unaffiliated_institution_get(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)

    def test_cannot_delete_if_nodes_affiliated(self):
        node = ProjectFactory(creator=self.user)
        node.affiliated_institutions.add(self.institution)

        redirect = self.view.delete(self.request)
        nt.assert_equal(redirect.url, '/institutions/{}/cannot_delete/'.format(self.institution.id))
        nt.assert_equal(redirect.status_code, 302)


class TestInstitutionChangeForm(AdminTestCase):
    def setUp(self):
        super(TestInstitutionChangeForm, self).setUp()

        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.InstitutionChangeForm()
        self.view = setup_form_view(self.view, self.request, form=InstitutionForm())

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get_context_data(self):
        self.view.object = self.institution
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_institution_form(self):
        new_data = {
            'name': 'New Name',
            'logo_name': 'awesome_logo.png',
            'domains': 'http://kris.biz/, http://www.little.biz/',
            '_id': 'newawesomeprov'
        }
        form = InstitutionForm(data=new_data)
        nt.assert_true(form.is_valid())


class TestInstitutionExport(AdminTestCase):
    def setUp(self):
        super(TestInstitutionExport, self).setUp()

        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionExport()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get(self):
        res = self.view.get(self.request)
        content_dict = json.loads(res.content)[0]
        nt.assert_equal(content_dict['model'], 'osf.institution')
        nt.assert_equal(content_dict['fields']['name'], self.institution.name)
        nt.assert_equal(res.__getitem__('content-type'), 'text/json')


class TestCreateInstitution(AdminTestCase):
    def setUp(self):
        super(TestCreateInstitution, self).setUp()

        self.user = AuthUserFactory()
        self.change_permission = Permission.objects.get(codename='change_institution')
        self.user.user_permissions.add(self.change_permission)
        self.user.save()

        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.base_view = views.CreateInstitution
        self.view = setup_form_view(self.base_view(), self.request, form=InstitutionForm())

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get_context_data(self):
        self.view.object = self.institution
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_no_permission_raises(self):
        user2 = AuthUserFactory()
        nt.assert_false(user2.has_perm('osf.change_institution'))
        self.request.user = user2

        with nt.assert_raises(PermissionDenied):
            self.base_view.as_view()(self.request)

    def test_get_view(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)


class TestAffiliatedNodeList(AdminTestCase):
    def setUp(self):
        super(TestAffiliatedNodeList, self).setUp()

        self.institution = InstitutionFactory()

        self.user = AuthUserFactory()
        self.view_node = Permission.objects.get(codename='view_node')
        self.user.user_permissions.add(self.view_node)
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.node1 = ProjectFactory(creator=self.user)
        self.node2 = ProjectFactory(creator=self.user)
        self.node1.affiliated_institutions.add(self.institution)
        self.node2.affiliated_institutions.add(self.institution)

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.base_view = views.InstitutionNodeList
        self.view = setup_form_view(self.base_view(), self.request, form=InstitutionForm())

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get_context_data(self):
        self.view.object_list = [self.node1, self.node2]
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['institution'], Institution)

    def test_no_permission_raises(self):
        user2 = AuthUserFactory()
        nt.assert_false(user2.has_perm('osf.view_node'))
        self.request.user = user2

        with nt.assert_raises(PermissionDenied):
            self.base_view.as_view()(self.request)

    def test_get_view(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)

    def test_get_queryset(self):
        nodes_returned = list(self.view.get_queryset())
        node_list = [self.node1, self.node2]
        nt.assert_equals(nodes_returned, node_list)
        nt.assert_is_instance(nodes_returned[0], Node)
