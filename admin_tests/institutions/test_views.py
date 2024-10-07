import json
from operator import itemgetter
from django.http import Http404
from django.urls import reverse
from nose import tools as nt
import mock
from django.test import RequestFactory
from django.contrib.auth.models import Permission, AnonymousUser
from django.core.exceptions import PermissionDenied

from addons.osfstorage.models import Region
from api.base import settings as api_settings
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
    RegionFactory
)
from osf.models import Institution, Node, UserQuota, OSFUser

from admin_tests.utilities import setup_form_view, setup_user_view, setup_view

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


class TestInstitutionUserList(AdminTestCase):

    def setUp(self):

        super(TestInstitutionUserList, self).setUp()
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/institution_list')
        self.view = views.InstitutionUserList()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_permission_unauthenticated(self):
        view = setup_user_view(views.InstitutionUserList(), self.request, user=AnonymousUser())
        permission_result = view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(view.raise_exception, False)

    def test_permission_user(self):
        view = setup_user_view(views.InstitutionUserList(), self.request, user=self.user)
        permission_result = view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(view.raise_exception, True)

    def test_permission_admin(self):
        self.user.is_staff = True
        self.user.save()
        view = setup_user_view(views.InstitutionUserList(), self.request, user=self.user)
        permission_result = view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(view.raise_exception, True)

    def test_permission_super_admin(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        view = setup_user_view(views.InstitutionUserList(), self.request, user=self.user)
        permission_result = view.test_func()
        nt.assert_equal(permission_result, True)

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


class TestGetUserListWithQuota(AdminTestCase):
    def setUp(self):
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.request = RequestFactory().get('/fake_path')
        self.view = setup_user_view(
            views.UserListByInstitutionID(),
            self.request,
            user=self.user,
            institution_id=self.institution.id
        )

    @mock.patch('website.util.quota.used_quota')
    def test_default_quota(self, mock_usedquota):
        mock_usedquota.return_value = 0

        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]
        nt.assert_equal(user_quota['quota'], api_settings.DEFAULT_MAX_QUOTA)

    def test_custom_quota(self):
        UserQuota.objects.create(user=self.user, storage_type=UserQuota.NII_STORAGE, max_quota=200)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]
        nt.assert_equal(user_quota['quota'], 200)

    def test_used_quota_bytes(self):
        UserQuota.objects.create(user=self.user, storage_type=UserQuota.NII_STORAGE, max_quota=100, used=560)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], 560)
        nt.assert_equal(round(user_quota['usage_value'], 1), 0.6)
        nt.assert_equal(user_quota['usage_abbr'], 'KB')

        nt.assert_equal(user_quota['remaining'], int(100 * api_settings.SIZE_UNIT_GB) - 560)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100)
        nt.assert_equal(user_quota['remaining_abbr'], 'GB')

        nt.assert_equal(round(user_quota['ratio'], 1), 0)

    def test_used_quota_giga(self):
        used = int(5.2 * api_settings.SIZE_UNIT_GB)
        UserQuota.objects.create(user=self.user, storage_type=UserQuota.NII_STORAGE, max_quota=100, used=used)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], used)
        nt.assert_equal(round(user_quota['usage_value'], 1), 5.2)
        nt.assert_equal(user_quota['usage_abbr'], 'GB')

        nt.assert_equal(user_quota['remaining'], 100 * api_settings.SIZE_UNIT_GB - used)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100 - 5.2)
        nt.assert_equal(user_quota['remaining_abbr'], 'GB')

        nt.assert_equal(round(user_quota['ratio'], 1), 5.2)

class TestGetUserListWithQuotaSorted(AdminTestCase):
    def setUp(self):
        self.institution = InstitutionFactory()
        self.users = []
        self.users.append(self.add_user(100, 80 * api_settings.SIZE_UNIT_GB))
        self.users.append(self.add_user(200, 90 * api_settings.SIZE_UNIT_GB))
        self.users.append(self.add_user(10, 10 * api_settings.SIZE_UNIT_GB))

    def add_user(self, max_quota, used):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution)
        user.save()
        UserQuota.objects.create(user=user, max_quota=max_quota, used=used)
        return user

    def view_get(self, url_params):
        request = RequestFactory().get('/fake_path?{}'.format(url_params))
        view = setup_user_view(
            views.UserListByInstitutionID(),
            request,
            user=self.users[0],
            institution_id=self.institution.id
        )
        return view.get(request)

    def test_sort_username_asc(self):
        expected = sorted(map(lambda u: u.username, self.users), reverse=False)
        response = self.view_get('order_by=username&status=asc')
        result = list(map(itemgetter('username'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_username_desc(self):
        expected = sorted(map(lambda u: u.username, self.users), reverse=True)
        response = self.view_get('order_by=username&status=desc')
        result = list(map(itemgetter('username'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_fullname_asc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=False)
        response = self.view_get('order_by=fullname&status=asc')
        result = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_fullname_desc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=True)
        response = self.view_get('order_by=fullname&status=desc')
        result = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_ratio_asc(self):
        expected = [45.0, 80.0, 100.0]
        response = self.view_get('order_by=ratio&status=asc')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_ratio_desc(self):
        expected = [100.0, 80.0, 45.0]
        response = self.view_get('order_by=ratio&status=desc')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_usage_asc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [10, 80, 90]))
        response = self.view_get('order_by=usage&status=asc')
        result = list(map(itemgetter('usage'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_usage_desc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [90, 80, 10]))
        response = self.view_get('order_by=usage&status=desc')
        result = list(map(itemgetter('usage'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_remaining_asc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [0, 20, 110]))
        response = self.view_get('order_by=remaining&status=asc')
        result = list(map(itemgetter('remaining'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_remaining_desc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [110, 20, 0]))
        response = self.view_get('order_by=remaining&status=desc')
        result = list(map(itemgetter('remaining'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_quota_asc(self):
        expected = [10, 100, 200]
        response = self.view_get('order_by=quota&status=asc')
        result = list(map(itemgetter('quota'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_quota_desc(self):
        expected = [200, 100, 10]
        response = self.view_get('order_by=quota&status=desc')
        result = list(map(itemgetter('quota'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_invalid(self):
        expected = [100.0, 80.0, 45.0]
        response = self.view_get('order_by=invalid&status=hello')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

class TestStatisticalStatusDefaultStorage(AdminTestCase):
    def setUp(self):
        self.institution01 = InstitutionFactory(name='inst01')

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.save()

        self.us = RegionFactory()
        self.us._id = self.institution01._id
        self.us.waterbutler_settings['storage']['type'] = Region.NII_STORAGE
        self.us.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = setup_user_view(
            views.StatisticalStatusDefaultStorage(),
            self.request,
            user=self.institution01_admin,
            institution_id=self.institution01.id
        )

    def test_unauthenticated(self):
        self.request.user = AnonymousUser()
        nt.assert_false(self.view.test_func())
        nt.assert_false(self.view.raise_exception)

    def test_user_login(self):
        self.request.user = self.normal_user
        nt.assert_false(self.view.test_func())
        nt.assert_true(self.view.raise_exception)

    def test_admin_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_admin_with_no_affiliated_institution_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.request.user.affiliated_institutions.clear()
        nt.assert_false(self.view.test_func())
        nt.assert_true(self.view.raise_exception)

    def test_super_admin_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_false(self.view.test_func())
        nt.assert_true(self.view.raise_exception)

    def test_institution_that_does_not_use_nii_storage(self):
        self.us.waterbutler_settings['storage']['type'] = Region.INSTITUTIONS
        self.us.save()
        with nt.assert_raises(Http404):
            self.view.get(self.request)

    def test_institution_deleted(self):
        self.institution01.is_deleted = True
        self.institution01.save()
        with nt.assert_raises(Http404):
            self.view.get(self.request)

    def test_anonymous_login(self):
        self.request.user = self.anon
        nt.assert_false(self.view.test_func())

    def test_normal_user_login(self):
        self.request.user = self.normal_user
        nt.assert_false(self.view.test_func())

    def test_superuser_login(self):
        self.request.user = self.superuser
        nt.assert_false(self.view.test_func())

    def test_admin_has_inst_login(self):
        self.request.user = self.institution01_admin
        nt.assert_true(self.view.test_func())

    def test_admin_not_inst_login(self):
        self.request.user = self.institution02_admin
        nt.assert_false(self.view.test_func())

    @mock.patch('website.util.quota.used_quota')
    def test_default_quota(self, mock_usedquota):
        mock_usedquota.return_value = 0

        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]
        nt.assert_equal(user_quota['quota'], api_settings.DEFAULT_MAX_QUOTA)

    def test_custom_quota(self):
        UserQuota.objects.create(user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE, max_quota=200)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]
        nt.assert_equal(user_quota['quota'], 200)

    def test_used_quota_bytes(self):
        UserQuota.objects.create(user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE, max_quota=100, used=560)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], 560)
        nt.assert_equal(round(user_quota['usage_value'], 1), 0.6)
        nt.assert_equal(user_quota['usage_abbr'], 'KB')

        nt.assert_equal(user_quota['remaining'], int(100 * api_settings.SIZE_UNIT_GB) - 560)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100)
        nt.assert_equal(user_quota['remaining_abbr'], 'GB')

        nt.assert_equal(round(user_quota['ratio'], 1), 0)

    def test_used_quota_giga(self):
        used = int(5.2 * api_settings.SIZE_UNIT_GB)
        UserQuota.objects.create(user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE, max_quota=100, used=used)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], used)
        nt.assert_equal(round(user_quota['usage_value'], 1), 5.2)
        nt.assert_equal(user_quota['usage_abbr'], 'GB')

        nt.assert_equal(user_quota['remaining'], 100 * api_settings.SIZE_UNIT_GB - used)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100 - 5.2)
        nt.assert_equal(user_quota['remaining_abbr'], 'GB')

        nt.assert_equal(round(user_quota['ratio'], 1), 5.2)

class TestStatisticalStatusDefaultStorageSorted(AdminTestCase):
    def setUp(self):
        self.institution = InstitutionFactory()

        self.us = RegionFactory()
        self.us._id = self.institution._id
        self.us.save()

        self.users = []
        self.users.append(self.add_user('test001-eppn', 100, 80 * api_settings.SIZE_UNIT_GB))
        self.users.append(self.add_user('test002-eppn', 200, 90 * api_settings.SIZE_UNIT_GB))
        self.users.append(self.add_user('test003-eppn', 10, 10 * api_settings.SIZE_UNIT_GB))

    def add_user(self, eppn, max_quota, used):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution)
        user.eppn = eppn
        user.save()
        UserQuota.objects.create(
            user=user,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=max_quota,
            used=used
        )
        return user

    def view_get(self, url_params):
        request = RequestFactory().get('/fake_path?{}'.format(url_params))
        view = setup_user_view(
            views.StatisticalStatusDefaultStorage(),
            request,
            user=self.users[0],
            institution_id=self.institution.id
        )
        return view.get(request)

    def test_sort_username_asc(self):
        expected = sorted(map(lambda u: u.username, self.users), reverse=False)
        response = self.view_get('order_by=username&status=asc')
        result = list(map(itemgetter('username'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_username_desc(self):
        expected = sorted(map(lambda u: u.username, self.users), reverse=True)
        response = self.view_get('order_by=username&status=desc')
        result = list(map(itemgetter('username'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_fullname_asc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=False)
        response = self.view_get('order_by=fullname&status=asc')
        result = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_fullname_desc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=True)
        response = self.view_get('order_by=fullname&status=desc')
        result = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_ratio_asc(self):
        expected = [45.0, 80.0, 100.0]
        response = self.view_get('order_by=ratio&status=asc')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_ratio_desc(self):
        expected = [100.0, 80.0, 45.0]
        response = self.view_get('order_by=ratio&status=desc')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_usage_asc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [10, 80, 90]))
        response = self.view_get('order_by=usage&status=asc')
        result = list(map(itemgetter('usage'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_usage_desc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [90, 80, 10]))
        response = self.view_get('order_by=usage&status=desc')
        result = list(map(itemgetter('usage'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_remaining_asc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [0, 20, 110]))
        response = self.view_get('order_by=remaining&status=asc')
        result = list(map(itemgetter('remaining'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_remaining_desc(self):
        expected = list(map(lambda x: x * api_settings.SIZE_UNIT_GB, [110, 20, 0]))
        response = self.view_get('order_by=remaining&status=desc')
        result = list(map(itemgetter('remaining'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_quota_asc(self):
        expected = [10, 100, 200]
        response = self.view_get('order_by=quota&status=asc')
        result = list(map(itemgetter('quota'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_quota_desc(self):
        expected = [200, 100, 10]
        response = self.view_get('order_by=quota&status=desc')
        result = list(map(itemgetter('quota'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_invalid(self):
        expected = [100.0, 80.0, 45.0]
        response = self.view_get('order_by=invalid&status=hello')
        result = list(map(itemgetter('ratio'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_eppn_asc(self):
        expected = sorted(map(lambda u: u.eppn, self.users), reverse=False)
        response = self.view_get('order_by=eppn&status=asc')
        result = list(map(itemgetter('eppn'), response.context_data['users']))
        nt.assert_equal(result, expected)

    def test_sort_eppn_desc(self):
        expected = sorted(map(lambda u: u.eppn, self.users), reverse=True)
        response = self.view_get('order_by=eppn&status=desc')
        result = list(map(itemgetter('eppn'), response.context_data['users']))
        nt.assert_equal(result, expected)


class TestUpdateQuotaUserListByInstitutionID(AdminTestCase):
    def setUp(self):
        super(TestUpdateQuotaUserListByInstitutionID, self).setUp()
        self.user1 = AuthUserFactory(fullname='fullname1', is_superuser=True, is_staff=True)
        self.institution = InstitutionFactory()
        self.user2 = AuthUserFactory()
        self.user2.affiliated_institutions.add(self.institution)
        self.user2.save()
        self.view = views.UpdateQuotaUserListByInstitutionID.as_view()

    def test_permission_unauthenticated(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = AnonymousUser()
        response = self.view(
            request,
            institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)
        nt.assert_in('login', str(response))

    def test_permission_user(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = AuthUserFactory()
        with nt.assert_raises(PermissionDenied):
            self.view(
                request,
                institution_id=self.institution.id
            )

    def test_permission_admin(self):
        self.user1.is_superuser = False
        self.user1.save()
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1
        with nt.assert_raises(PermissionDenied):
            self.view(
                request,
                institution_id=self.institution.id
            )

    def test_permission_super_admin(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        nt.assert_not_in('login', str(response))

    def test_post_max_quota_none(self):
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {})
        request.user = self.user1
        response = self.view(
            request,
            institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)

        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_none(user_quota)

    def test_post_max_quota_invalid(self):
        max_quota = 'test'
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1
        response = self.view(
            request,
            institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)

        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_none(user_quota)

    def test_post_max_quota_negative(self):
        max_quota = -100
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1
        response = self.view(
            request,
            institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)

        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_none(user_quota)

    def test_post_max_quota_too_large(self):
        max_quota = 1000000000000
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_none(user_quota)

    def test_post_institution_not_found(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': 0}),
            {'maxQuota': max_quota})
        request.user = self.user1
        with nt.assert_raises(Http404):
            self.view(
                request,
                institution_id=0
            )

    def test_post_institution_not_using_nii_storage(self):
        region = RegionFactory(_id=self.institution.guid)
        region.waterbutler_settings['storage']['type'] = Region.INSTITUTIONS
        region.save()
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1
        with nt.assert_raises(Http404):
            self.view(
                request,
                institution_id=self.institution.id
            )

    def test_post_create_quota(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)
        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test_post_update_quota(self):
        UserQuota.objects.create(user=self.user1, max_quota=100)
        max_quota = 150
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        user_quota = UserQuota.objects.filter(
            user=self.user2, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test__post_update_quota_institution_id_not_exist(self):
        max_quota = 150
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': 0}),
            {'maxQuota': max_quota})
        request.user = self.user1
        with nt.assert_raises(Http404):
            self.view(request, institution_id=0)


class TestQuotaUserList(AdminTestCase):
    def setUp(self):
        super(TestQuotaUserList, self).setUp()
        self.user = AuthUserFactory(fullname='fullname')
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = views.QuotaUserList()
        self.view.get_userlist = self.get_userlist
        self.view.request = self.request
        self.view.paginate_by = 10
        self.view.kwargs = {}
        self.view.object_list = self.view.get_queryset()

    def get_institution(self):
        return self.institution

    def get_institution_has_storage_name(self):
        query = 'select name '\
                'from addons_osfstorage_region '\
                'where addons_osfstorage_region._id = osf_institution._id'
        institution = Institution.objects.filter(
            id=self.institution.id).extra(
            select={
                'storage_name': query,
            }
        )
        return institution.first()

    def get_userlist(self):
        user_list = []
        for user in OSFUser.objects.filter(
                affiliated_institutions=self.institution.id):
            user_list.append(self.view.get_user_quota_info(
                user, UserQuota.CUSTOM_STORAGE)
            )
        return user_list

    def test_get_user_quota_info_eppn_is_none(self):
        default_value_eppn = ''
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)
        response = self.view.get_user_quota_info(
            self.user,
            storage_type=UserQuota.CUSTOM_STORAGE
        )

        nt.assert_is_not_none(response['eppn'])
        nt.assert_equal(response['eppn'], default_value_eppn)

    def test_get_user_quota_info_max_quota_zero(self):
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=0)
        response = self.view.get_user_quota_info(
            self.user,
            storage_type=UserQuota.CUSTOM_STORAGE
        )

        nt.assert_is_not_none(response['ratio'])
        nt.assert_equal(response['ratio'], 100)

    def test_get_context_data_has_not_storage_name(self):
        self.view.get_institution = self.get_institution
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)

        response = self.view.get_context_data()

        nt.assert_is_instance(response, dict)
        nt.assert_false('institution_storage_name' in response)

    def test_get_context_data_has_storage_name(self):
        self.view.get_institution = self.get_institution_has_storage_name
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)

        response = self.view.get_context_data()

        nt.assert_is_instance(response, dict)
        nt.assert_true('institution_storage_name' in response)


class TestUserListByInstitutionID(AdminTestCase):

    def setUp(self):
        super(TestUserListByInstitutionID, self).setUp()
        self.user = AuthUserFactory(fullname='Alex fullname')
        self.user2 = AuthUserFactory(fullname='Kenny Dang')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.UserListByInstitutionID()
        self.view = setup_view(self.view,
                               self.request,
                               institution_id=self.institution.id)

    def test_permission_unauthenticated(self):
        self.request.user = AnonymousUser()
        permission_result = self.view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(self.view.raise_exception, False)

    def test_permission_user(self):
        permission_result = self.view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(self.view.raise_exception, True)

    def test_permission_admin(self):
        self.user.is_staff = True
        self.user.save()
        self.request.user = self.user
        permission_result = self.view.test_func()
        nt.assert_equal(permission_result, False)
        nt.assert_equal(self.view.raise_exception, True)

    def test_permission_super_admin(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.request.user = self.user
        permission_result = self.view.test_func()
        nt.assert_equal(permission_result, True)

    def test_default_user_list_by_institution_id(self, *args, **kwargs):

        res = self.view.get_userlist()
        nt.assert_is_instance(res, list)

    def test_default_user_list_by_institution_id_not_found(self, *args, **kwargs):
        view = setup_view(self.view,
                          self.request,
                          institution_id=0)
        with nt.assert_raises(Http404):
            view.get_userlist()

    def test_default_user_list_by_institution_id_that_does_not_use_nii_storage(self, *args, **kwargs):
        region = RegionFactory(_id=self.institution.guid)
        region.waterbutler_settings['storage']['type'] = Region.INSTITUTIONS
        region.save()
        with nt.assert_raises(Http404):
            self.view.get_userlist()

    def test_search_email_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': self.user2.username
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['username'], self.user2.username)
        nt.assert_equal(len(res), 1)

    def test_search_guid_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'guid': self.user2._id
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user2._id)
        nt.assert_equal(len(res), 1)

    def test_search_name_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'info': 'kenny'
            }
        )
        request.user = self.user

        view = views.UserListByInstitutionID()
        view = setup_view(view, request, institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 1)
        nt.assert_in(res[0]['fullname'], self.user2.fullname)

    def test_search_name_guid_email_inputted(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'test@gmail.com',
                'guid': self.user._id,
                'info': 'kenny'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user._id)
        nt.assert_in(res[0]['fullname'], self.user.fullname)
        nt.assert_equal(len(res), 1)

    def test_search_not_found(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'sstest@gmail.com',
                'guid': 'guid2',
                'info': 'guid2'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 0)

    def test_search_institution_id_not_exist(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': 0}),
            {
                'email': 'sstest@gmail.com',
                'guid': 'guid2',
                'info': 'guid2'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=0)
        with nt.assert_raises(Http404):
            view.get_userlist()


class TestExportFileTSV(AdminTestCase):
    def setUp(self):
        super(TestExportFileTSV, self).setUp()
        self.user = AuthUserFactory(fullname='Kenny Michel',
                                    username='Kenny@gmail.com')
        self.user2 = AuthUserFactory(fullname='alex queen')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()
        self.view = views.ExportFileTSV()

    def test_get(self):
        request = RequestFactory().get(
            'institutions:tsvexport',
            kwargs={'institution_id': self.institution.id})
        request.user = self.user
        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/tsv')
        nt.assert_in('kenny', result)
        nt.assert_in('alex queen', result)
        nt.assert_in('kenny@gmail.com', result)

    def test_get_institution_id_not_exist(self):
        request = RequestFactory().get(
            'institutions:tsvexport',
            kwargs={'institution_id': 0})
        request.user = self.user
        view = setup_view(self.view, request,
                          institution_id=0)
        with nt.assert_raises(Http404):
            view.get(request)

    def test_get_zero_max_quota(self):
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.NII_STORAGE,
                                 max_quota=0)
        request = RequestFactory().get(
            'institutions:tsvexport',
            kwargs={'institution_id': self.institution.id})
        request.user = self.user
        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/tsv')
        nt.assert_in('100', result)


class TestRecalculateQuota(AdminTestCase):
    def setUp(self):
        super(TestRecalculateQuota, self).setUp()

        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()

        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution1)
        self.institution1.save()
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.url = reverse('institutions:institution_list')
        self.view = views.RecalculateQuota()
        self.view.request = self.request

    def test_permission_unauthenticated(self):
        self.request.user = AnonymousUser()
        nt.assert_false(self.view.test_func())
        nt.assert_false(self.view.raise_exception)

    def test_permission_user(self):
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_false(self.view.test_func())
        nt.assert_true(self.view.raise_exception)

    def test_permission_admin(self):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_false(self.view.test_func())
        nt.assert_true(self.view.raise_exception)

    def test_permission_super_admin(self):
        nt.assert_true(self.view.test_func())

    @mock.patch('website.util.quota.update_user_used_quota')
    @mock.patch('admin.institutions.views.OSFUser.objects')
    def test_post_method(self, mock_osfuser, mock_update_user_used_quota_method):
        mock_osfuser.filter.return_value = [self.user]

        response = self.view.post(request=self.request)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_osfuser.filter.assert_called()
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    @mock.patch('admin.institutions.views.OSFUser.objects')
    def test_post_method_update_to_custom_storage_quota(self, mock_osfuser, mock_update_user_used_quota_method):
        region = RegionFactory(_id=self.institution1.guid)
        region.waterbutler_settings['storage']['type'] = Region.NII_STORAGE
        region.save()
        mock_osfuser.filter.return_value = [self.user]

        response = self.view.post(request=self.request)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_osfuser.filter.assert_called()
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    @mock.patch('admin.institutions.views.OSFUser.objects')
    def test_post_method_with_institution_id(self, mock_osfuser, mock_update_user_used_quota_method):
        mock_osfuser.filter.return_value = [self.user]
        response = self.view.post(request=self.request, institution_id=self.institution1.id)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, reverse('institutions:institution_user_list', kwargs={'institution_id': self.institution1.id}))
        mock_osfuser.filter.assert_called()
        mock_update_user_used_quota_method.assert_called()

    def test_post_method_with_institution_id__not_found(self):
        with nt.assert_raises(Http404):
            self.view.post(request=self.request, institution_id=-1)

    def test_post_method_with_institution_id__not_using_nii_storage(self):
        region = RegionFactory(_id=self.institution1.guid)
        region.waterbutler_settings['storage']['type'] = Region.INSTITUTIONS
        region.save()
        with nt.assert_raises(Http404):
            self.view.post(request=self.request, institution_id=self.institution1.id)
