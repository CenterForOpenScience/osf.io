from nose import tools as nt

from django.test import RequestFactory
#from django.core.urlresolvers import reverse, reverse_lazy
#from django.utils import timezone
#from django.urls import reverse

from tests.base import AdminTestCase
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
)

from admin.rdm_timestampadd import views
from admin_tests.utilities import setup_user_view
from website.views import userkey_generation
from osf.models import RdmUserKey, RdmFileTimestamptokenVerifyResult, Guid, BaseFileNode
from api.base import settings as api_settings
import os
#import json
from tests.test_views import create_rdmfiletimestamptokenverifyresult


class TestInstitutionList(AdminTestCase):
    def setUp(self):
        super(TestInstitutionList, self).setUp()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.user = AuthUserFactory()

        self.request_url = '/timestampadd/'
        self.request = RequestFactory().get(self.request_url)
        self.view = views.InstitutionList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institutions[0].id}
        self.redirect_url = '/timestampadd/' + str(self.view.kwargs['institution_id']) + '/nodes/'

    def test_super_admin_get(self, *args, **kwargs):
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_is_instance(res.context_data['view'], views.InstitutionList)

    def test_admin_get(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.request.user.affiliated_institutions.add(self.institutions[0])
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 302)
        nt.assert_in(self.redirect_url, str(res))


class TestInstitutionNodeList(AdminTestCase):
    def setUp(self):
        super(TestInstitutionNodeList, self).setUp()
        self.user = AuthUserFactory()

        ## create project(affiliated institution)
        self.project_institution = InstitutionFactory()
        self.project_user = UserFactory()
        userkey_generation(self.project_user._id)
        self.project_user.affiliated_institutions.add(self.project_institution)
        # project1 timestamp_pattern_division=1
        self.private_project1 = ProjectFactory(creator=self.project_user)
        self.private_project1.affiliated_institutions.add(self.project_institution)
        # project2 timestamp_pattern_division=2
        self.private_project2 = ProjectFactory(creator=self.project_user)
        self.private_project2.affiliated_institutions.add(self.project_institution)

        self.request = RequestFactory().get('/timestampadd/' + str(self.project_institution.id) + '/nodes/')
        self.view = views.InstitutionNodeList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.project_institution.id}

    def tearDown(self):
        super(TestInstitutionNodeList, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.project_user._id).object_id
        self.project_user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_get_context_data(self, **kwargs):
        self.view.object_list = self.view.get_queryset()
        kwargs = {'object_list': self.view.object_list}
        res = self.view.get_context_data(**kwargs)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(len(res['nodes']), 2)
        nt.assert_is_instance(res['view'], views.InstitutionNodeList)


class TestTimeStampAddList(AdminTestCase):
    def setUp(self):
        super(TestTimeStampAddList, self).setUp()
        self.user = AuthUserFactory()

        ## create project(affiliated institution)
        self.project_institution = InstitutionFactory()
        self.project_user = UserFactory()
        userkey_generation(self.project_user._id)
        self.project_user.affiliated_institutions.add(self.project_institution)
        self.user = self.project_user
        # project1 timestamp_pattern_division=1
        self.private_project1 = ProjectFactory(creator=self.project_user)
        self.private_project1.affiliated_institutions.add(self.project_institution)
        self.node = self.private_project1

        self.request = RequestFactory().get('/timestampadd/' + str(self.project_institution.id) + '/nodes/' + str(self.private_project1.id) + '/')
        self.view = views.TimeStampAddList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.project_institution.id}

        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file1.status_1', provider='osfstorage', inspection_result_status_1=True)
        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file2.status_3', provider='osfstorage', inspection_result_status_1=False)
        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file3.status_3', provider='osfstorage', inspection_result_status_1=False)
        create_rdmfiletimestamptokenverifyresult(self, filename='s3_test_file1.status_3', provider='s3', inspection_result_status_1=False)

    def tearDown(self):
        super(TestTimeStampAddList, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.project_user._id).object_id
        self.project_user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_get_context_data(self, **kwargs):
        self.view.kwargs['guid'] = self.private_project1.id
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)

        ## check TimestampError(TimestampVerifyResult.inspection_result_statu != 1) in response
        nt.assert_not_in('osfstorage_test_file1.status_1', str(res))
        nt.assert_in('osfstorage_test_file2.status_3', str(res))
        nt.assert_in('osfstorage_test_file3.status_3', str(res))
        nt.assert_in('s3_test_file1.status_3', str(res))
        nt.assert_is_instance(res['view'], views.TimeStampAddList)


#class TestVerifyTimeStampAddList(AdminTestCase):


class TestTimestampVerifyData(AdminTestCase):
    def setUp(self):
        super(TestTimestampVerifyData, self).setUp()
        self.user = AuthUserFactory()

        ## create project(affiliated institution)
        self.project_institution = InstitutionFactory()
        self.project_user = UserFactory()
        userkey_generation(self.project_user._id)
        self.project_user.affiliated_institutions.add(self.project_institution)
        self.user = self.project_user
        # project1 timestamp_pattern_division=1
        self.private_project1 = ProjectFactory(creator=self.project_user)
        self.private_project1.affiliated_institutions.add(self.project_institution)
        self.node = self.private_project1
        self.request_url = '/timestampadd/' + str(self.project_institution.id) + '/nodes/' + str(self.private_project1.id) + '/verify/verify_data/'

    def tearDown(self):
        super(TestTimestampVerifyData, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.project_user._id).object_id
        self.project_user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_post(self, **kwargs):
        from api_tests.utils import create_test_file

        file_node = create_test_file(node=self.node, user=self.user, filename='test_get_timestamp_error_data')
        self.post_data = {
            'provider': [str(file_node.provider)],
            'file_id': [str(file_node._id)],
            'file_path': [str('/' + file_node.name)],
            'file_name': [str(file_node.name)],
            'version': [str(file_node.current_version_number)]
        }
        self.view = views.TimestampVerifyData()
        self.request = RequestFactory().post(self.request_url, data=self.post_data, format='json')
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs['institution_id'] = self.project_institution.id
        self.view.kwargs['guid'] = self.private_project1.id
        self.private_project1.reload()

        res = self.view.post(self, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_in('test_get_timestamp_error_data', str(res))


class TestAddTimestampData(AdminTestCase):
    def setUp(self):
        super(TestAddTimestampData, self).setUp()
        self.user = AuthUserFactory()

        ## create project(affiliated institution)
        self.project_institution = InstitutionFactory()
        self.project_user = UserFactory()
        userkey_generation(self.project_user._id)
        self.project_user.affiliated_institutions.add(self.project_institution)
        self.user = self.project_user
        # project1 timestamp_pattern_division=1
        self.private_project1 = ProjectFactory(creator=self.project_user)
        self.private_project1.affiliated_institutions.add(self.project_institution)
        self.node = self.private_project1

        self.request_url = '/timestampadd/' + str(self.project_institution.id) + '/nodes/' + str(self.private_project1.id) + '/'
        self.request = RequestFactory().get(self.request_url)
        self.view = views.TimeStampAddList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs['institution_id'] = self.project_institution.id
        self.view.kwargs['guid'] = self.private_project1.id

        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file1.status_1', provider='osfstorage', inspection_result_status_1=True)
        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file2.status_3', provider='osfstorage', inspection_result_status_1=False)
        create_rdmfiletimestamptokenverifyresult(self, filename='osfstorage_test_file3.status_3', provider='osfstorage', inspection_result_status_1=False)
        create_rdmfiletimestamptokenverifyresult(self, filename='s3_test_file1.status_3', provider='s3', inspection_result_status_1=False)

    def tearDown(self):
        super(TestAddTimestampData, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.project_user._id).object_id
        self.project_user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_post(self, **kwargs):
        res_timestampaddlist = self.view.get_context_data()
        nt.assert_is_instance(res_timestampaddlist, dict)

        ## check TimestampError(TimestampVerifyResult.inspection_result_statu != 1) in response
        nt.assert_not_in('osfstorage_test_file1.status_1', str(res_timestampaddlist))
        nt.assert_in('osfstorage_test_file2.status_3', str(res_timestampaddlist))
        nt.assert_in('osfstorage_test_file3.status_3', str(res_timestampaddlist))
        nt.assert_in('s3_test_file1.status_3', str(res_timestampaddlist))
        nt.assert_is_instance(res_timestampaddlist['view'], views.TimeStampAddList)

        ## AddTimestampData.post
        file_node = BaseFileNode.objects.get(name='osfstorage_test_file3.status_3')
        file_verify_result = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        self.post_data = {
            'provider': [file_verify_result.provider],
            'file_id': [file_verify_result.file_id],
            'file_path': [file_verify_result.path],
            'file_name': [file_node.name],
            'version': [file_node.current_version_number]
        }
        self.request_url_addtimestamp = '/timestampadd/' + str(self.project_institution.id) + '/nodes/' + str(self.private_project1.id) + '/addtimestamp/add_timestamp_data/'
        self.view_addtimestamp = views.AddTimestampData()
        self.request_addtimestamp = RequestFactory().post(self.request_url_addtimestamp, data=self.post_data, format='json')
        self.view_addtimestamp = setup_user_view(self.view_addtimestamp, self.request_addtimestamp, user=self.user)
        self.view_addtimestamp.kwargs['institution_id'] = self.project_institution.id
        self.view_addtimestamp.kwargs['guid'] = self.private_project1.id
        self.private_project1.reload()

        res_addtimestamp = self.view_addtimestamp.post(self, **kwargs)
        nt.assert_equal(res_addtimestamp.status_code, 200)
        nt.assert_in('osfstorage_test_file3.status_3', str(res_addtimestamp))
        nt.assert_in('"verify_result": 1', str(res_addtimestamp))

        res_timestampaddlist = self.view.get_context_data()
        nt.assert_not_in('osfstorage_test_file1.status_1', str(res_timestampaddlist))
        nt.assert_in('osfstorage_test_file2.status_3', str(res_timestampaddlist))
        nt.assert_not_in('osfstorage_test_file3.status_3', str(res_timestampaddlist))
        nt.assert_in('s3_test_file1.status_3', str(res_timestampaddlist))
        nt.assert_is_instance(res_timestampaddlist['view'], views.TimeStampAddList)
