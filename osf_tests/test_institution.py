from nose import tools as nt
from past.builtins import basestring
from addons.osfstorage.models import Region
from osf.models import Institution, UserQuota
from tests.base import AdminTestCase
from .factories import (
    InstitutionFactory,
    AuthUserFactory,
    ExportDataLocationFactory,
    RegionFactory,
)
import pytest


@pytest.mark.django_db
def test_factory():
    inst = InstitutionFactory()
    assert isinstance(inst.name, basestring)
    assert len(inst.domains) > 0
    assert len(inst.email_domains) > 0


@pytest.mark.django_db
def test_querying_on_domains():
    inst = InstitutionFactory(domains=['foo.test'])
    result = Institution.objects.filter(domains__contains=['foo.test'])
    assert inst in result


@pytest.mark.django_db
def test_institution_banner_path_none():
    inst = InstitutionFactory(banner_name='kittens.png')
    assert inst.banner_path is not None
    inst.banner_name = None
    assert inst.banner_path is None


@pytest.mark.django_db
def test_institution_logo_path_none():
    inst = InstitutionFactory(logo_name='kittens.png')
    assert inst.logo_path is not None
    inst.logo_name = None
    assert inst.logo_path is None


@pytest.mark.django_db
def test_institution_logo_path():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields/osf-shield.png'
    assert inst.logo_path == expected_logo_path


@pytest.mark.django_db
def test_institution_logo_path_rounded_corners():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields-rounded-corners/osf-shield-rounded-corners.png'
    assert inst.logo_path_rounded_corners == expected_logo_path


@pytest.mark.django_db
def test_institution_banner_path():
    inst = InstitutionFactory(banner_name='osf-banner.png')
    expected_banner_path = '/static/img/institutions/banners/osf-banner.png'
    assert inst.banner_path == expected_banner_path


class TestInstitutionPermissions:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution_admin_user(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.mark.django_db
    def test_group_member_has_perms(self, institution, institution_admin_user):
        assert institution_admin_user.has_perm('view_institutional_metrics', institution)

    @pytest.mark.django_db
    def test_non_group_member_doesnt_have_perms(self, institution, user):
        assert user.has_perm('view_institutional_metrics', institution) is False


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestInstitution(AdminTestCase):

    def test_institution_guid(self):
        institution = InstitutionFactory()
        nt.assert_equal(institution.guid, institution._id)

    def test_get_default_storage_location(self):
        institution = InstitutionFactory()
        res = institution.get_default_storage_location()
        nt.assert_equal(len(list(res)), 0)

        # default location
        ExportDataLocationFactory(institution_guid=Institution.INSTITUTION_DEFAULT)
        res = institution.get_default_storage_location()
        nt.assert_equal(len(list(res)), 1)

    def test_get_institutional_storage_location(self):
        institution = InstitutionFactory()
        res = institution.get_institutional_storage_location()
        nt.assert_equal(len(list(res)), 0)

        # institutional location
        ExportDataLocationFactory(institution_guid=institution.guid)
        res = institution.get_institutional_storage_location()
        nt.assert_equal(len(list(res)), 1)

    def test_get_allowed_storage_location(self):
        institution = InstitutionFactory()
        res = institution.get_allowed_storage_location()
        nt.assert_equal(len(list(res)), 0)

        # default location
        ExportDataLocationFactory(institution_guid=Institution.INSTITUTION_DEFAULT)
        res = institution.get_default_storage_location()
        nt.assert_equal(len(list(res)), 1)
        res = institution.get_allowed_storage_location()
        nt.assert_equal(len(list(res)), 1)

        # institutional location
        ExportDataLocationFactory(institution_guid=institution.guid)
        res = institution.get_institutional_storage_location()
        nt.assert_equal(len(list(res)), 1)
        res = institution.get_allowed_storage_location()
        nt.assert_equal(len(list(res)), 2)

    def test_have_institutional_storage_location_id(self):
        institution = InstitutionFactory()
        res = institution.have_institutional_storage_location_id(0)
        nt.assert_false(res)

        # default location
        location = ExportDataLocationFactory(institution_guid=Institution.INSTITUTION_DEFAULT)
        res = institution.have_institutional_storage_location_id(location.id)
        nt.assert_false(res)

        # institutional location
        location = ExportDataLocationFactory(institution_guid=institution.guid)
        res = institution.have_institutional_storage_location_id(location.id)
        nt.assert_true(res)

    def test_have_allowed_storage_location_id(self):
        institution = InstitutionFactory()
        res = institution.have_allowed_storage_location_id(0)
        nt.assert_false(res)

        # default location
        location = ExportDataLocationFactory(institution_guid=Institution.INSTITUTION_DEFAULT)
        res = institution.have_allowed_storage_location_id(location.id)
        nt.assert_true(res)

        # institutional location
        location = ExportDataLocationFactory(institution_guid=institution.guid)
        res = institution.have_allowed_storage_location_id(location.id)
        nt.assert_true(res)

    def test_get_institutional_storage(self):
        institution = InstitutionFactory()
        res = institution.get_institutional_storage()
        nt.assert_equals(len(list(res)), 1)

        RegionFactory(_id=institution.guid)
        res = institution.get_institutional_storage()
        nt.assert_equals(len(list(res)), 2)

    def test_get_allowed_institutional_storage(self):
        institution = InstitutionFactory()
        res = institution.get_allowed_institutional_storage()
        nt.assert_equals(len(list(res)), 1)

        RegionFactory(_id=institution.guid)
        res = institution.get_allowed_institutional_storage()
        nt.assert_equals(len(list(res)), 2)

    def test_get_default_region(self):
        institution = InstitutionFactory()
        res = institution.get_default_region()
        first_source = institution.get_institutional_storage().first()
        nt.assert_equals(res, first_source)

        last_source = RegionFactory(_id=institution.guid)
        res = institution.get_default_region()
        nt.assert_equals(res, first_source)
        nt.assert_equals(institution.get_institutional_storage().last(), last_source)
        nt.assert_not_equals(res, last_source)

    def test_get_default_institutional_storage(self):
        institution = InstitutionFactory()
        res = institution.get_default_institutional_storage()
        first_source = institution.get_institutional_storage().first()
        nt.assert_equals(res, first_source)

        last_source = RegionFactory(_id=institution.guid)
        res = institution.get_default_institutional_storage()
        nt.assert_equals(res, first_source)
        nt.assert_equals(institution.get_institutional_storage().last(), last_source)
        nt.assert_not_equals(res, last_source)

    def test_is_allowed_institutional_storage_id(self):
        institution = InstitutionFactory()
        res = institution.is_allowed_institutional_storage_id(0)
        nt.assert_false(res)

        # default source storage
        source = RegionFactory(_id=Institution.INSTITUTION_DEFAULT)
        res = institution.is_allowed_institutional_storage_id(source.id)
        nt.assert_false(res)

        # institutional source storage
        source = RegionFactory(_id=institution.guid)
        res = institution.is_allowed_institutional_storage_id(source.id)
        nt.assert_true(res)

    def test_get_user_quota_type_for_nii_storage__nii_default_storage(self):
        institution = InstitutionFactory()
        user_quota_type = institution.get_user_quota_type_for_nii_storage()
        nt.assert_equal(user_quota_type, UserQuota.NII_STORAGE)

    def test_get_user_quota_type_for_nii_storage__nii_custom_storage(self):
        institution = InstitutionFactory()
        region = RegionFactory(_id=institution._id)
        region.waterbutler_settings['storage']['type'] = Region.NII_STORAGE
        region.save()

        user_quota_type = institution.get_user_quota_type_for_nii_storage()
        nt.assert_equal(user_quota_type, UserQuota.CUSTOM_STORAGE)

    def test_get_user_quota_type_for_nii_storage__not_using_nii_storage(self):
        institution = InstitutionFactory()
        region = RegionFactory(_id=institution._id)
        region.waterbutler_settings['storage']['type'] = Region.INSTITUTIONS
        region.save()

        user_quota_type = institution.get_user_quota_type_for_nii_storage()
        nt.assert_is_none(user_quota_type)
