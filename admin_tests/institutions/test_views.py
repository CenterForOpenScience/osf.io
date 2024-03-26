import json
import pytest

from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory
)
from osf.models import Institution, Node, AbstractNode

from admin_tests.utilities import setup_form_view, setup_user_view

from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm


class TestInstitutionList(AdminTestCase):
    def setUp(self):
        super().setUp()

        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user = AuthUserFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionList()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_get_list(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        assert res.status_code == 200

    def test_get_queryset(self):
        institutions_returned = list(self.view.get_queryset())
        inst_list = [self.institution1, self.institution2]
        assert set(institutions_returned) == set(inst_list)
        assert isinstance(institutions_returned[0], Institution)

    def test_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        assert isinstance(res, dict)
        assert len(res['institutions']) == 2
        assert isinstance(res['institutions'][0], Institution)


class TestInstitutionDisplay(AdminTestCase):
    def setUp(self):
        super().setUp()

        self.user = AuthUserFactory()

        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionDisplay()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get_object(self):
        obj = self.view.get_object()
        assert isinstance(obj, Institution)
        assert obj.name == self.institution.name

    def test_context_data(self):
        res = self.view.get_context_data()
        assert isinstance(res, dict)
        assert isinstance(res['institution'], dict)
        assert res['institution']['name'] == self.institution.name
        assert isinstance(res['change_form'], InstitutionForm)
        assert isinstance(res['import_form'], ImportFileForm)

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        assert res.status_code == 200


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
        assert redirect.url == '/institutions/'
        assert redirect.status_code == 302

    def test_unaffiliated_institution_get(self):
        res = self.view.get(self.request)
        assert res.status_code == 200

    def test_cannot_delete_if_nodes_affiliated(self):
        node = ProjectFactory(creator=self.user)
        node.affiliated_institutions.add(self.institution)

        redirect = self.view.delete(self.request)
        assert redirect.url == f'/institutions/{self.institution.id}/cannot_delete/'
        assert redirect.status_code == 302


class TestInstitutionChangeForm(AdminTestCase):
    def setUp(self):
        super().setUp()

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
        assert isinstance(res, dict)
        assert isinstance(res['import_form'], ImportFileForm)

    def test_institution_form(self):
        new_data = {
            'name': 'New Name',
            'logo_name': 'awesome_logo.png',
            'domains': 'http://kris.biz/, http://www.little.biz/',
            '_id': 'newawesomeprov'
        }
        form = InstitutionForm(data=new_data)
        assert form.is_valid()


class TestInstitutionExport(AdminTestCase):
    def setUp(self):
        super().setUp()

        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionExport()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'institution_id': self.institution.id}

    def test_get(self):
        res = self.view.get(self.request)
        content_dict = json.loads(res.content)[0]
        assert content_dict['model'] == 'osf.institution'
        assert content_dict['fields']['name'] == self.institution.name
        assert res.__getitem__('content-type') == 'text/json'

class TestCreateInstitution(AdminTestCase):
    def setUp(self):
        super().setUp()

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
        assert isinstance(res, dict)
        assert isinstance(res['import_form'], ImportFileForm)

    def test_no_permission_raises(self):
        user2 = AuthUserFactory()
        assert not user2.has_perm('osf.change_institution')
        self.request.user = user2

        with pytest.raises(PermissionDenied):
            self.base_view.as_view()(self.request)

    def test_get_view(self):
        res = self.view.get(self.request)
        assert res.status_code == 200


class TestAffiliatedNodeList(AdminTestCase):
    def setUp(self):
        super().setUp()

        self.institution = InstitutionFactory()

        self.user = AuthUserFactory()
        self.view_node = Permission.objects.filter(
            codename='view_node',
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        ).first()
        self.user.user_permissions.add(self.view_node)
        self.user.add_or_update_affiliated_institution(self.institution)
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
        assert isinstance(res, dict)
        assert isinstance(res['institution'], Institution)

    def test_no_permission_raises(self):
        user2 = AuthUserFactory()
        assert not user2.has_perm('osf.view_node')
        self.request.user = user2

        with pytest.raises(PermissionDenied):
            self.base_view.as_view()(self.request)

    def test_get_view(self):
        res = self.view.get(self.request)
        assert res.status_code == 200

    def test_get_queryset(self):
        nodes_returned = list(self.view.get_queryset())
        node_list = [self.node1, self.node2]
        assert nodes_returned == node_list
        assert isinstance(nodes_returned[0], Node)
