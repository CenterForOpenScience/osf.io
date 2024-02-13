from urllib.parse import urlencode

import mock
import pytest
from admin.entitlements import views
from admin_tests.utilities import setup_user_view
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db.models.query import QuerySet
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt
from osf.models.institution_entitlement import InstitutionEntitlement
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    InstitutionEntitlementFactory,
)
from tests.base import AdminTestCase
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.http import HttpResponseBadRequest

pytestmark = pytest.mark.django_db


class TestInstitutionEntitlementList(AdminTestCase):
    def setUp(self):
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')

        self.change_permission = Permission.objects.get(codename='admin_institution_entitlement')

        # Not login user
        self.anon = AnonymousUser()

        # Admin user
        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.user_permissions.add(self.change_permission)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.user_permissions.add(self.change_permission)
        self.institution02_admin.save()

        # Super user
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.is_superuser = True
        self.user_2.save()

        self.user = AuthUserFactory()
        self.user.save()

        self.request = RequestFactory().get('/fake_path')

        self.view = views.InstitutionEntitlementList()

    def test_get_context_data_is_super_admin(self):
        self.institution = InstitutionFactory()
        self.institution.name = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.institutionEntitlement = InstitutionEntitlementFactory(institution=self.institution,
                                                                    login_availability=True, modifier=self.user_2)
        self.institution.save()

        request = RequestFactory().get('/fake_path', kwargs={'institution_id': self.institution.id})

        self.view.request = request
        self.view.request.user = self.user_2
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()

        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['institutions'][0].id, self.institution.id)
        nt.assert_equal(res['selected_id'], self.institution.id)
        nt.assert_is_instance(res['entitlements'], QuerySet)
        nt.assert_is_instance(res['entitlements'][0], InstitutionEntitlement)
        nt.assert_equal(res['entitlements'][0], self.institutionEntitlement)

    def test_get_context_data_is_admin_and_has_affiliated_institutions(self):
        self.institution = InstitutionFactory()
        self.institution.name = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.institutionEntitlement = InstitutionEntitlementFactory(institution=self.institution,
                                                                    login_availability=True, modifier=self.user_2)
        self.institution.save()

        self.user_2.is_staff = True
        self.user_2.is_superuser = False
        self.user_2.affiliated_institutions.add(self.institution)
        self.user_2.save()

        request = RequestFactory().get('/fake_path', kwargs={'institution_id': self.institution.id})
        self.view.request = request
        self.view.request.user = self.user_2
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()

        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['institutions'][0].id, self.institution.id)
        nt.assert_equal(res['selected_id'], self.institution.id)
        nt.assert_is_instance(res['entitlements'], QuerySet)
        nt.assert_is_instance(res['entitlements'][0], InstitutionEntitlement)
        nt.assert_equal(res['entitlements'][0], self.institutionEntitlement)

    def test_get_context_data_raise_PermissionDenied(self):
        self.institution = InstitutionFactory()
        self.institution.name = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.institutionEntitlement = InstitutionEntitlementFactory(institution=self.institution,
                                                                    login_availability=True, modifier=self.user_2)
        self.institution.save()

        self.user_2.is_staff = False
        self.user_2.is_superuser = False
        self.user_2.save()

        request = RequestFactory().get('/fake_path', kwargs={'institution_id': self.institution.id})
        self.view.request = request
        self.view.request.user = self.user_2
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view.object_list = self.view.get_queryset()

        with self.assertRaises(PermissionDenied):
            self.view.get_context_data()

    def test_get_queryset(self):
        institution1 = InstitutionFactory()
        institution2 = InstitutionFactory()
        institution_entitlement1 = InstitutionEntitlementFactory(institution=institution1, login_availability=True)
        institution_entitlement2 = InstitutionEntitlementFactory(institution=institution2, login_availability=True)
        self.view = setup_user_view(self.view, self.request, user=self.user)

        institution_entitlements = list(self.view.get_queryset())

        institution_entitlement_list = [institution_entitlement1, institution_entitlement2]
        # Create a list ordered by entitlement
        institution_entitlement_list = sorted(institution_entitlement_list, key=lambda item: item.entitlement)

        nt.assert_equals(set(institution_entitlements), set(institution_entitlement_list))
        nt.assert_is_instance(institution_entitlements[0], InstitutionEntitlement)
        nt.assert_equal(len(self.view.get_queryset()), 2)

    def test_InstitutionEntitlementList_correct_view_permissions(self):
        user = AuthUserFactory()
        user.is_superuser = True

        self.institution = InstitutionFactory()
        self.institution.name = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.institutionEntitlement = InstitutionEntitlementFactory(institution=self.institution,
                                                                    login_availability=True, modifier=user)
        self.institution.save()

        self.view_permission = views.InstitutionEntitlementList

        change_permission = Permission.objects.get(codename='admin_institution_entitlement')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('institutions:entitlements'))
        request.user = user

        response = self.view_permission.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_InstitutionEntitlementList_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(reverse('institutions:entitlements'))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.InstitutionEntitlementList.as_view()(request)

    def test_InstitutionEntitlementList_anonymous(self):
        request = RequestFactory().get(reverse('institutions:entitlements'))
        request.user = self.anon

        with self.assertRaises(PermissionDenied):
            views.InstitutionEntitlementList.as_view()(request)

    def test_InstitutionEntitlementList_admin_with_permission(self):
        self.view_permission = views.InstitutionEntitlementList
        request = RequestFactory().get(reverse('institutions:entitlements')
                                        + '?institution_id=' + str(self.institution01.id))
        request.user = self.institution01_admin

        response = self.view_permission.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_InstitutionEntitlementList_admin_without_permission(self):
        # institution_id not same institution of login user
        request = RequestFactory().get(reverse('institutions:entitlements')
                                        + '?institution_id=' + str(self.institution01.id))
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            views.InstitutionEntitlementList.as_view()(request)

        # admin not in institution
        request = RequestFactory().get(reverse('institutions:entitlements')
                                        + '?institution_id=' + str(self.institution01.id))
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            views.InstitutionEntitlementList.as_view()(request)

    def test_InstitutionEntitlementList_not_exist_institution(self):
        request = RequestFactory().get(reverse('institutions:entitlements') + '?institution_id=1234')
        request.user = self.user_2

        with self.assertRaises(Http404):
            views.InstitutionEntitlementList.as_view()(request)

    @mock.patch('admin.entitlements.views.render_bad_request_response')
    def test_InstitutionEntitlementList_not_valid_institution(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        request = RequestFactory().get(reverse('institutions:entitlements') + '?institution_id=fake_id')
        request.user = self.user_2

        response = views.InstitutionEntitlementList.as_view()(request)
        self.assertEqual(response.status_code, 400)


class TestBulkAddInstitutionEntitlement(AdminTestCase):

    def setUp(self):
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')
        self.entitlement_1 = InstitutionEntitlementFactory(institution=self.institution01)
        self.entitlement_2 = InstitutionEntitlementFactory(institution=self.institution02)

        self.anon = AnonymousUser()

        self.change_permission = Permission.objects.get(codename='admin_institution_entitlement')

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.user_permissions.add(self.change_permission)
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.user_permissions.add(self.change_permission)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.user_permissions.add(self.change_permission)
        self.institution02_admin.save()

        self.view = views.BulkAddInstitutionEntitlement.as_view()
        self.view_permission = views.BulkAddInstitutionEntitlement

    @mock.patch('admin.entitlements.views.InstitutionEntitlement.objects.create')
    def test_post_entitlement_find(self, mockApi):
        request = RequestFactory().post(
            reverse('entitlements:bulk_add'), {
                'institution_id': self.institution01.id,
                'entitlements': ['gkn1-ent111'],
                'login_availability': ['on']
            }
        )

        self.entitlement_1.institution_id = self.institution01.id
        self.entitlement_1.entitlement = 'gkn1-ent111'
        self.entitlement_1.save()

        request.user = self.institution01_admin
        response = self.view(request)

        mockApi.assert_not_called()
        nt.assert_equal(response.status_code, 302)

    @mock.patch('admin.entitlements.views.InstitutionEntitlement.objects.create')
    def test_post_entitlement_not_found(self, mockApi):
        request = RequestFactory().post(
            reverse('entitlements:bulk_add'), {
                'institution_id': self.institution01.id,
                'entitlements': ['gkn1-ent11', 'gkn1-ent12', 'gkn1-ent13'],
                'login_availability': ['on', 'on', 'on']
            }
        )
        request.user = self.institution01_admin

        response = self.view(request)

        mockApi.assert_called()
        nt.assert_equal(response.status_code, 302)

    @pytest.mark.skip
    def test_BulkAddInstitutionEntitlement_no_user_permissions_raises_error(self):
        user = AuthUserFactory()

        request = RequestFactory().post(reverse('entitlements:bulk_add'))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request)

    def test_BulkAddInstitutionEntitlement_correct_view_permissions(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.is_staff = True
        user.save()

        change_permission = Permission.objects.get(codename='admin_institution_entitlement')
        user.user_permissions.add(change_permission)
        user.save()
        data = {'institution_id': institution.id,
                'entitlements': 'demo',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = user

        response = self.view_permission.as_view()(request)
        self.assertEqual(response.status_code, 302)

    def test_permission_anonymous(self):
        request = RequestFactory().post(reverse('entitlements:bulk_add'))
        request.user = self.anon

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request)

    def test_permission_normal_user(self):
        data = {'institution_id': self.institution01.id,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.normal_user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request)

    def test_permission_super(self):
        data = {'institution_id': self.institution01.id,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.superuser
        response = self.view_permission.as_view()(request)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_with_permission(self):
        data = {'institution_id': self.institution01.id,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.institution01_admin
        response = self.view_permission.as_view()(request)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_without_permission(self):
        data = {'institution_id': self.institution01.id,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request)

    def test_permission_not_exist_inst(self):
        data = {'institution_id': 0,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request)

    @mock.patch('admin.entitlements.views.render_bad_request_response')
    def test__institution_id_none(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        data = {'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.superuser
        result = self.view_permission.as_view()(request)
        self.assertEqual(result.status_code, 400)

    @mock.patch('admin.entitlements.views.render_bad_request_response')
    def test__institution_id_invalid_format(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        data = {'institution_id': 'fake_id',
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.superuser
        result = self.view_permission.as_view()(request)
        self.assertEqual(result.status_code, 400)

    @mock.patch('admin.entitlements.views.render_bad_request_response')
    def test__institution_id_not_exist(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        data = {'institution_id': 0,
                'entitlements': 'demo super',
                'login_availability': 'on'
                }
        request = RequestFactory().post(reverse('entitlements:bulk_add'), data=data)
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request)


class TestToggleInstitutionEntitlement(AdminTestCase):

    def setUp(self):
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')
        self.entitlement_1 = InstitutionEntitlementFactory(institution=self.institution01)
        self.entitlement_2 = InstitutionEntitlementFactory(institution=self.institution02)

        self.anon = AnonymousUser()

        self.change_permission = Permission.objects.get(codename='admin_institution_entitlement')

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.user_permissions.add(self.change_permission)
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.user_permissions.add(self.change_permission)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.user_permissions.add(self.change_permission)
        self.institution02_admin.save()

        self.view = views.ToggleInstitutionEntitlement.as_view()
        self.view_permission = views.ToggleInstitutionEntitlement

    def test_post_method(self):
        url = reverse('institutions:entitlement_toggle',
                      kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        request = RequestFactory().post(url)
        request.user = self.superuser

        response = self.view(request,
                             institution_id=self.institution01.id,
                             entitlement_id=self.entitlement_1.id)

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.institution01.id, 'page': 1})

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, '{}?{}'.format(base_url, query_string))

    @pytest.mark.skip
    def test_ToggleInstitutionEntitlement_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request)

    def test_ToggleInstitutionEntitlement_correct_view_permissions(self):
        user = AuthUserFactory()

        change_permission = Permission.objects.get(codename='admin_institution_entitlement')
        user.user_permissions.add(change_permission)
        user.is_staff = True
        user.affiliated_institutions.add(self.institution01)
        user.save()

        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = user

        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_permission_anonymous(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.anon

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_normal_user(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.normal_user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_super(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.superuser
        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_with_permission(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution01_admin
        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_without_permission(self):
        # institution_id not same institution of login user
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

        # admin not in institution
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_super_not_exist_inst(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': 0, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request,
                                           institution_id=0, entitlement_id=self.entitlement_1.id)

    def test_permission_super_not_exist_entitlement(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': 0})
        )
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request,
                                            institution_id=self.institution01.id, entitlement_id=0)

    def test_permission_with_entitlement_not_in_institution(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_2.id})
        )
        request.user = self.superuser
        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                            institution_id=self.institution01.id,
                                            entitlement_id=self.entitlement_2.id)

    def test_permission_admin_not_exist_inst(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': 0, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution01_admin
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request, institution_id=0,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_admin_not_exist_entitlement(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_toggle',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': 0})
        )
        request.user = self.institution01_admin
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id, entitlement_id=0)


class TestDeleteInstitutionEntitlement(AdminTestCase):

    def setUp(self):
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')
        self.entitlement_1 = InstitutionEntitlementFactory(institution=self.institution01)
        self.entitlement_2 = InstitutionEntitlementFactory(institution=self.institution02)

        self.anon = AnonymousUser()

        self.change_permission = Permission.objects.get(codename='admin_institution_entitlement')

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.user_permissions.add(self.change_permission)
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.user_permissions.add(self.change_permission)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.user_permissions.add(self.change_permission)
        self.institution02_admin.save()

        self.view = views.DeleteInstitutionEntitlement.as_view()
        self.view_permission = views.DeleteInstitutionEntitlement

    @pytest.mark.skip
    def test_DeleteInstitutionEntitlement_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get('/fake_path')
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request, institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_DeleteInstitutionEntitlement_correct_view_permissions(self):
        user = AuthUserFactory()

        change_permission = Permission.objects.get(codename='admin_institution_entitlement')
        user.user_permissions.add(change_permission)
        user.affiliated_institutions.add(self.institution01)
        user.is_staff = True
        user.save()

        request = RequestFactory().post(reverse('institutions:entitlement_delete',
                                                kwargs={'institution_id': self.institution01.id,
                                                        'entitlement_id': self.entitlement_1.id})
                                        )
        request.user = user

        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_post_method(self):
        url = reverse('institutions:entitlement_delete',
                      kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        request = RequestFactory().post(url)
        request.user = self.superuser

        response = self.view(request,
                             institution_id=self.institution01.id,
                             entitlement_id=self.entitlement_1.id)

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.institution01.id, 'page': 1})

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, '{}?{}'.format(base_url, query_string))

    def test_permission_anonymous(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.anon

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_normal_user(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.normal_user

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_super(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.superuser
        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_with_permission(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution01_admin
        response = self.view_permission.as_view()(request,
                                                  institution_id=self.institution01.id,
                                                  entitlement_id=self.entitlement_1.id)
        self.assertEqual(response.status_code, 302)

    def test_permission_admin_without_permission(self):
        # institution_id not same institution of login user
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

        # admin not in institution
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_1.id})
        )
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin

        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_super_not_exist_inst(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': 0, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request, institution_id=0,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_super_not_exist_entitlement(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': 0})
        )
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id, entitlement_id=0)

    def test_permission_with_entitlement_not_in_institution(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': self.entitlement_2.id})
        )
        request.user = self.superuser
        with self.assertRaises(PermissionDenied):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id,
                                           entitlement_id=self.entitlement_2.id)

    def test_permission_admin_not_exist_inst(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': 0, 'entitlement_id': self.entitlement_1.id})
        )
        request.user = self.institution01_admin
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request, institution_id=0,
                                           entitlement_id=self.entitlement_1.id)

    def test_permission_admin_not_exist_entitlement(self):
        request = RequestFactory().post(
            reverse('institutions:entitlement_delete',
                    kwargs={'institution_id': self.institution01.id, 'entitlement_id': 0})
        )
        request.user = self.institution01_admin
        with self.assertRaises(Http404):
            self.view_permission.as_view()(request,
                                           institution_id=self.institution01.id, entitlement_id=0)
