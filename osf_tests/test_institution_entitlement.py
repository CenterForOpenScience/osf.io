from osf.models.institution_entitlement import InstitutionEntitlement
from nose import tools as nt
from .factories import InstitutionFactory, InstitutionEntitlementFactory, AuthUserFactory
import pytest


class TestInstitutionEntitlementModel:

    @pytest.mark.django_db
    def test_factory(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        inst = InstitutionEntitlementFactory(institution=institution, login_availability=True, modifier=user)
        nt.assert_equal(inst.institution, institution)
        nt.assert_equal(inst.login_availability, True)
        nt.assert_equal(inst.modifier, user)

    @pytest.mark.django_db
    def test__init__(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        institution_entitlement = InstitutionEntitlement(institution=institution, login_availability=True, modifier=user)
        nt.assert_equal(institution_entitlement.institution, institution)
        nt.assert_equal(institution_entitlement.login_availability, True)
        nt.assert_equal(institution_entitlement.modifier, user)

    @pytest.mark.django_db
    def test__unitcode__(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        inst = InstitutionEntitlementFactory(institution=institution, login_availability=True, modifier=user)
        expectedResult = u'institution_{}:{}'.format(inst.institution._id, inst.entitlement)
        nt.assert_equal(inst.__unicode__(), expectedResult)
