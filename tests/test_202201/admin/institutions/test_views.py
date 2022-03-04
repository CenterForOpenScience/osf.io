import json
from operator import itemgetter
from django.urls import reverse
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


class TestUpdateQuotaUserListByInstitutionID(AdminTestCase):
    def setUp(self):
        super(TestUpdateQuotaUserListByInstitutionID, self).setUp()
        self.user1 = AuthUserFactory(fullname='fullname1')
        view_permission = Permission.objects.get(codename='change_osfuser')
        self.user1.user_permissions.add(view_permission)
        self.institution = InstitutionFactory()
        self.user1.affiliated_institutions.add(self.institution)
        self.user1.save()

        self.view = views.UpdateQuotaUserListByInstitutionID.as_view()

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
            user=self.user1, storage_type=UserQuota.NII_STORAGE
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
            user=self.user1, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test_UpdateQuotaUserListByInstitutionID_correct_view_permission(self):
        user = AuthUserFactory()

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': 20})

        request.user = user

        response = views.UpdateQuotaUserListByInstitutionID.as_view()(
            request, institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)

    def test_UpdateQuotaUserListByInstitutionID_permission_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': 20})
        request.user = user

        with nt.assert_raises(PermissionDenied):
            views.UpdateQuotaUserListByInstitutionID.as_view()(
                request, institution_id=self.institution.id
            )
