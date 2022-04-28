import pytest
from api.base.settings.defaults import API_BASE
from nose import tools as nt
from osf_tests.factories import InstitutionFactory, AuthUserFactory, InstitutionEntitlementFactory


@pytest.mark.django_db
class TestLoginAvailability:

    def test_post_serializer_valid(self, app):
        self.institution = InstitutionFactory()
        self.institution.save()

        self.institution_entitlement1 = InstitutionEntitlementFactory(institution=self.institution)
        self.institution_entitlement2 = InstitutionEntitlementFactory(institution=self.institution)
        self.institution_entitlement3 = InstitutionEntitlementFactory(institution=self.institution)

        self.institution_entitlement1.save()
        self.institution_entitlement2.save()
        self.institution_entitlement3.save()

        self.user = AuthUserFactory()
        self.user.save()
        url = '/{0}institutions/login_availability/'.format(API_BASE)
        data = {
            'institution_id': self.institution._id,
            'entitlements': [self.institution_entitlement1.entitlement, self.institution_entitlement2.entitlement,
                             self.institution_entitlement3.entitlement]
        }

        res = app.simple_post_api(url, data, expect_errors=True)
        res_data = res.json['login_availability']
        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res_data, False)

    def test_post_serializer_invalid(self, app):
        self.institution = InstitutionFactory()
        self.institution.save()

        self.institution_entitlement1 = InstitutionEntitlementFactory(institution=self.institution)
        self.institution_entitlement2 = InstitutionEntitlementFactory(institution=self.institution)
        self.institution_entitlement3 = InstitutionEntitlementFactory(institution=self.institution)

        self.institution_entitlement1.save()
        self.institution_entitlement2.save()
        self.institution_entitlement3.save()

        self.user = AuthUserFactory()
        self.user.save()
        url = '/{0}institutions/login_availability/'.format(API_BASE)
        data = {
            'institution_id': self.institution._id,
            'entitlements': [True, False, True]
        }

        res = app.simple_post_api(url, data, expect_errors=True)
        nt.assert_equal(res.status_code, 400)
