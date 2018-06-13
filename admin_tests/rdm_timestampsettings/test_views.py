from nose import tools as nt

from django.test import RequestFactory
#from django.core.urlresolvers import reverse, reverse_lazy
#from django.utils import timezone

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, AuthUserFactory, InstitutionFactory, ProjectFactory


from admin.rdm_timestampsettings import views
from admin_tests.utilities import setup_user_view
from website.views import userkey_generation
from osf.models import RdmUserKey, RdmTimestampGrantPattern, Guid
from api.base import settings as api_settings
import os


class TestInstitutionList(AdminTestCase):
    def setUp(self):
        super(TestInstitutionList, self).setUp()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.user = AuthUserFactory()

        self.request_url = '/timestampsettings/'
        self.request = RequestFactory().get(self.request_url)
        self.view = views.InstitutionList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institutions[0].id}
        self.redirect_url = '/timestampsettings/' + str(self.view.kwargs['institution_id']) + '/nodes/'

    def test_super_admin_get(self, *args, **kwargs):
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_is_instance(res.context_data['view'], views.InstitutionList)

    def test_admin_get(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.user.affiliated_institutions.add(self.institutions[0])
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
        RdmTimestampGrantPattern.objects.get_or_create(institution_id=self.project_institution.id, node_guid=self.private_project1._id, timestamp_pattern_division=1)
        # project2 timestamp_pattern_division=2
        self.private_project2 = ProjectFactory(creator=self.project_user)
        self.private_project2.affiliated_institutions.add(self.project_institution)
        RdmTimestampGrantPattern.objects.get_or_create(institution_id=self.project_institution.id, node_guid=self.private_project2._id, timestamp_pattern_division=2)

        self.request = RequestFactory().get('/timestampsettings/' + str(self.project_institution.id) + '/')
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
        for node in res['nodes']:
            timestampPattern = RdmTimestampGrantPattern.objects.get(node_guid=node['node']._id)
            nt.assert_equal(node['timestamppattern'].timestamp_pattern_division, timestampPattern.timestamp_pattern_division)
        nt.assert_is_instance(res['view'], views.InstitutionNodeList)


class TestInstitutionTimeStampPatternForce(AdminTestCase):
    def setUp(self):
        super(TestInstitutionTimeStampPatternForce, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/timestampsettings/')

        self.view = views.InstitutionTimeStampPatternForce()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_get(self, *args, **kwargs):
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        kwargs = {
            'institution_id': self.institution.id,
            'timestamp_pattern_division': 2,
            'forced': 1,
        }
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        timestampPattern = RdmTimestampGrantPattern.objects.get(institution_id=self.institution.id, node_guid__isnull=True)
        nt.assert_equal(int(kwargs['institution_id']), timestampPattern.institution_id)
        nt.assert_equal(int(kwargs['timestamp_pattern_division']), timestampPattern.timestamp_pattern_division)
        nt.assert_equal(bool(int(kwargs['forced'])), timestampPattern.is_forced)


class TestNodeTimeStampPatternChange(AdminTestCase):
    def setUp(self):
        super(TestNodeTimeStampPatternChange, self).setUp()
        self.user = AuthUserFactory()

        ## create project(affiliated institution)
        self.project_institution = InstitutionFactory()
        self.project_user = UserFactory()
        userkey_generation(self.project_user._id)
        self.project_user.affiliated_institutions.add(self.project_institution)
        # project1 timestamp_pattern_division=1
        self.private_project1 = ProjectFactory(creator=self.project_user)
        self.private_project1.affiliated_institutions.add(self.project_institution)
        RdmTimestampGrantPattern.objects.get_or_create(institution_id=self.project_institution.id, node_guid=self.private_project1._id, timestamp_pattern_division=1)

        self.request = RequestFactory().get('/timestampsettings/' + str(self.project_institution.id) + '/')
        self.view = views.NodeTimeStampPatternChange()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.project_institution.id}

    def tearDown(self):
        super(TestNodeTimeStampPatternChange, self).tearDown()
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

    def test_get(self, *args, **kwargs):
        timestampPattern = RdmTimestampGrantPattern.objects.get(node_guid=self.private_project1._id)
        nt.assert_equal(timestampPattern.timestamp_pattern_division, 1)
        kwargs = {
            'institution_id': self.project_institution.id,
            'guid': self.private_project1._id,
            'timestamp_pattern_division': 2,
        }
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        timestampPattern = RdmTimestampGrantPattern.objects.get(node_guid=self.private_project1._id)
        nt.assert_equal(timestampPattern.timestamp_pattern_division, 2)
