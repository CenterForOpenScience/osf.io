import json
from operator import itemgetter

from nose import tools as nt
import mock
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from api.base import settings as api_settings
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
    RegionFactory
)
from osf.models import Institution, Node, UserQuota

from admin_tests.utilities import setup_form_view, setup_user_view

from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm
from addons.osfstorage.models import Region


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
        nt.assert_items_equal(institutions_returned, inst_list)
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

    def test_get_list(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_queryset(self):
        institutions_returned = list(self.view.get_queryset())
        inst_list = [self.institution1, self.institution2]
        nt.assert_items_equal(institutions_returned, inst_list)
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
        nt.assert_items_equal(nodes_returned, node_list)
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
        UserQuota.objects.create(user=self.user, max_quota=200)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]
        nt.assert_equal(user_quota['quota'], 200)

    def test_used_quota_bytes(self):
        UserQuota.objects.create(user=self.user, max_quota=100, used=560)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], 560)
        nt.assert_equal(round(user_quota['usage_value'], 1), 0.5)
        nt.assert_equal(user_quota['usage_abbr'], 'KiB')

        nt.assert_equal(user_quota['remaining'], int(100 * 1024 ** 3) - 560)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100)
        nt.assert_equal(user_quota['remaining_abbr'], 'GiB')

        nt.assert_equal(round(user_quota['ratio'], 1), 0)

    def test_used_quota_giga(self):
        used = int(5.2 * 1024 ** 3)
        UserQuota.objects.create(user=self.user, max_quota=100, used=used)
        response = self.view.get(self.request)
        user_quota = response.context_data['users'][0]

        nt.assert_equal(user_quota['usage'], used)
        nt.assert_equal(round(user_quota['usage_value'], 1), 5.2)
        nt.assert_equal(user_quota['usage_abbr'], 'GiB')

        nt.assert_equal(user_quota['remaining'], 100 * 1024 ** 3 - used)
        nt.assert_equal(round(user_quota['remaining_value'], 1), 100 - 5.2)
        nt.assert_equal(user_quota['remaining_abbr'], 'GiB')

        nt.assert_equal(round(user_quota['ratio'], 1), 5.2)

class TestGetUserListWithQuotaSorted(AdminTestCase):
    def setUp(self):
        self.institution = InstitutionFactory()
        self.users = []
        self.users.append(self.add_user(100, 80 * 1024 ** 3))
        self.users.append(self.add_user(200, 90 * 1024 ** 3))
        self.users.append(self.add_user(10, 10 * 1024 ** 3))

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
        result = map(itemgetter('username'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_username_desc(self):
        expected = sorted(map(lambda u: u.username, self.users), reverse=True)
        response = self.view_get('order_by=username&status=desc')
        result = map(itemgetter('username'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_fullname_asc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=False)
        response = self.view_get('order_by=fullname&status=asc')
        result = map(itemgetter('fullname'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_fullname_desc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=True)
        response = self.view_get('order_by=fullname&status=desc')
        result = map(itemgetter('fullname'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_ratio_asc(self):
        expected = [45.0, 80.0, 100.0]
        response = self.view_get('order_by=ratio&status=asc')
        result = map(itemgetter('ratio'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_ratio_desc(self):
        expected = [100.0, 80.0, 45.0]
        response = self.view_get('order_by=ratio&status=desc')
        result = map(itemgetter('ratio'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_usage_asc(self):
        expected = map(lambda x: x * 1024 ** 3, [10, 80, 90])
        response = self.view_get('order_by=usage&status=asc')
        result = map(itemgetter('usage'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_usage_desc(self):
        expected = map(lambda x: x * 1024 ** 3, [90, 80, 10])
        response = self.view_get('order_by=usage&status=desc')
        result = map(itemgetter('usage'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_remaining_asc(self):
        expected = map(lambda x: x * 1024 ** 3, [0, 20, 110])
        response = self.view_get('order_by=remaining&status=asc')
        result = map(itemgetter('remaining'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_remaining_desc(self):
        expected = map(lambda x: x * 1024 ** 3, [110, 20, 0])
        response = self.view_get('order_by=remaining&status=desc')
        result = map(itemgetter('remaining'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_quota_asc(self):
        expected = [10, 100, 200]
        response = self.view_get('order_by=quota&status=asc')
        result = map(itemgetter('quota'), response.context_data['users'])
        nt.assert_equal(result, expected)

    def test_sort_quota_desc(self):
        expected = [200, 100, 10]
        response = self.view_get('order_by=quota&status=desc')
        result = map(itemgetter('quota'), response.context_data['users'])
        nt.assert_equal(result, expected)


class InstitutionDefaultStorageDisplay(AdminTestCase):
    def setUp(self):
        super(InstitutionDefaultStorageDisplay, self).setUp()
        import logging
        self.logger = logging.getLogger(__name__)
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.us = RegionFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionDefaultStorageDisplay()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution.id}

    def tearDown(self):
        super(InstitutionDefaultStorageDisplay, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution)
        self.institution.delete()
        self.us.delete()
        self.user.delete()

    def test_default_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['region'], Region)
        nt.assert_equal(res['institution'], self.institution._id)
        nt.assert_equal((res['region']).name, 'United States')

    def test_with_id_context_data(self):
        self.us = RegionFactory()
        self.us._id = self.institution._id
        self.us.save()
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['region'], Region)
        nt.assert_equal(res['institution'], self.institution._id)
        nt.assert_equal((res['region']).name, self.us.name)
        nt.assert_equal((res['region'])._id, self.us._id)

    def test_post(self, *args, **kwargs):
        new_region = RegionFactory()
        new_region._id = self.institution._id
        new_region.name = 'China'
        new_region.mfr_url = 'http://ec2-13-114-64-85.ap-northeast-1.compute.amazonaws.com:7778'
        form_data = {
            'name': new_region.name,
            'waterbutler_credentials': json.dumps(new_region.waterbutler_credentials).replace('true', 'True'),
            'waterbutler_settings': json.dumps(new_region.waterbutler_settings).replace('true', 'True'),
            'waterbutler_url': new_region.waterbutler_url,
            '_id': new_region._id,
            'institution': self.institution._id,
            'mfr_url': 'http://ec2-13-114-64-85.ap-northeast-1.compute.amazonaws.com:7778',
        }
        self.request_post = RequestFactory().post('/fake_path', form_data)
        self.view_post = views.InstitutionDefaultStorageDetail()
        self.view_post = setup_user_view(self.view_post, self.request_post, user=self.user)
        self.view_post.kwargs = form_data
        response_for_insert = self.view_post.post(self.request_post, *args, **self.view_post.kwargs)
        nt.assert_equal(response_for_insert.status_code, 302)
        nt.assert_equal(Region.objects.get(_id=self.institution._id).name, new_region.name)
        new_region.name = 'Taipe'
        count = Region.objects.count()
        form_data = {
            'name': new_region.name,
            'waterbutler_credentials': str(new_region.waterbutler_credentials).replace('true', 'True'),
            'waterbutler_settings': str(new_region.waterbutler_settings).replace('true', 'True'),
            'waterbutler_url': new_region.waterbutler_url,
            '_id': new_region._id,
            'institution': self.institution._id,
            'mfr_url': 'http://ec2-13-114-64-85.ap-northeast-1.compute.amazonaws.com:7778',
        }
        self.request_post = RequestFactory().post('/fake_path', form_data)
        self.view_post = views.InstitutionDefaultStorageDetail()
        self.view_post = setup_user_view(self.view_post, self.request_post, user=self.user)
        self.view_post.kwargs = form_data
        response_for_update = self.view_post.post(self.request_post, *args, **self.view_post.kwargs)
        nt.assert_equal(response_for_update.status_code, 302)
        nt.assert_equal(Region.objects.get(_id=self.institution._id).name, new_region.name)
        nt.assert_equal(Region.objects.count(), count)

    def test_get(self, *args, **kwargs):
        self.us = RegionFactory()
        self.us._id = self.institution._id
        self.us.save()
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_is_instance(res.context_data['region'], Region)
        nt.assert_equal(res.context_data['institution'], self.institution._id)
        nt.assert_equal((res.context_data['region']).name, self.us.name)
        nt.assert_equal((res.context_data['region'])._id, self.us._id)
        nt.assert_equal(res.status_code, 200)
