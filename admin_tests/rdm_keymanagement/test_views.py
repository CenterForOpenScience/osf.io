from nose import tools as nt

from django.test import RequestFactory
#from django.core.urlresolvers import reverse, reverse_lazy
from django.utils import timezone

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, AuthUserFactory, InstitutionFactory


from admin.rdm_keymanagement import views
from admin_tests.utilities import setup_user_view
from website.views import userkey_generation
from osf.models import RdmUserKey, Guid
from api.base import settings as api_settings
import os

import logging
logger = logging.getLogger(__name__)


class TestInstitutionList(AdminTestCase):
    def setUp(self):
        super(TestInstitutionList, self).setUp()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.user = AuthUserFactory()

        self.request_url = '/keymanagement/'
        self.request = RequestFactory().get(self.request_url)
        self.view = views.InstitutionList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institutions[0].id}
        self.redirect_url = '/keymanagement/' + str(self.view.kwargs['institution_id']) + '/'

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


class TestRemoveUserKeyList(AdminTestCase):
    def setUp(self):
        super(TestRemoveUserKeyList, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()

        ## delete_uusers
        self.delete_user1 = UserFactory()
        self.delete_user2 = UserFactory()
        self.delete_users = [self.delete_user1, self.delete_user2]
        for user in self.delete_users:
            userkey_generation(user._id)
            user.affiliated_institutions.add(self.institution)
            user.is_delete = True
            user.date_disabled = timezone.now()
            user.save()

        self.request = RequestFactory().get('/keymanagement/' + str(self.institution.id) + '/')
        self.view = views.RemoveUserKeyList()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution.id}

    def tearDown(self):
        super(TestRemoveUserKeyList, self).tearDown()
        for user in self.view.object_list:
            osfuser_id = Guid.objects.get(_id=user._id).object_id
            user.delete()

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
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(len(res['remove_key_users']), 2)
        nt.assert_is_instance(res['view'], views.RemoveUserKeyList)


class TestRemoveUserKey(AdminTestCase):
    def setUp(self):
        super(TestRemoveUserKey, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')

        self.delete_user = UserFactory()
        userkey_generation(self.delete_user._id)
        self.delete_user.affiliated_institutions.add(self.institution)
        self.delete_user.is_delete = True
        self.delete_user.date_disabled = timezone.now()
        self.delete_user.save()

        self.view = views.RemoveUserKey()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'user_id': self.delete_user.id, 'institution_id': self.institution.id}

    def tearDown(self):
        super(TestRemoveUserKey, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.delete_user._id).object_id
        self.delete_user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)

        update_datas = RdmUserKey.objects.filter(guid=self.view.kwargs['user_id'])
        for update_data in update_datas:
            nt.assert_equal(update_data.delete_flag, 1)
        nt.assert_equal(update_datas.count(), 2)
