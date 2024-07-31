import json

import jwe
import jwt
import pytest

from django.utils import timezone

from api.base import settings
from api.base.settings.defaults import API_BASE
from api.institutions.authentication import INSTITUTION_SHARED_SSO_MAP

from framework.auth import signals, Auth
from framework.auth.core import get_user
from framework.auth.views import send_confirm_email_async

from osf.models import OSFUser, InstitutionAffiliation, InstitutionStorageRegion
from osf.models.institution import SsoFilterCriteriaAction
from osf_tests.factories import InstitutionFactory, ProjectFactory, UserFactory, RegionFactory

from tests.base import capture_signals


def make_user(username, fullname):
    return UserFactory(username=username, fullname=fullname)


def make_payload(
        institution,
        sso_email,
        fullname='Fake User',
        given_name='',
        family_name='',
        middle_names='',
        suffix='',
        sso_identity='',
        department='',
        is_member_of='',
        user_roles='',
        selective_sso_filter='',
):

    data = {
        'provider': {
            'id': institution._id,
            'user': {
                'ssoIdentity': sso_identity,
                'ssoEmail': sso_email,
                'fullname': fullname,
                'familyName': family_name,
                'givenName': given_name,
                'middleNames': middle_names,
                'suffix': suffix,
                'department': department,
                'isMemberOf': is_member_of,
                'userRoles': user_roles,
                'selectiveSsoFilter': selective_sso_filter,
            }
        }
    }

    return jwe.encrypt(
        jwt.encode(
            {
                'sub': sso_email,
                'data': json.dumps(data)
            },
            settings.JWT_SECRET,
            algorithm='HS256'
        ).encode(),
        settings.JWE_SECRET
    )


@pytest.fixture()
def institution():
    return InstitutionFactory()


@pytest.fixture()
def institution_region():
    return RegionFactory()


@pytest.fixture()
def institution_region_preferred():
    return RegionFactory()


@pytest.fixture()
def user_default_region():
    user = UserFactory()
    return user.addons_osfstorage_user_settings.default_region


@pytest.fixture()
def institution_without_user_default_region(institution_region, institution_region_preferred):
    institution = InstitutionFactory()
    institution.storage_regions.add(institution_region)
    InstitutionStorageRegion.objects.create(
        institution=institution,
        storage_region=institution_region_preferred,
        is_preferred=True
    )
    return institution


@pytest.fixture()
def institution_with_default_user_region(user_default_region, institution_region_preferred):
    institution = InstitutionFactory()
    institution.storage_regions.add(user_default_region)
    InstitutionStorageRegion.objects.create(
        institution=institution,
        storage_region=institution_region_preferred,
        is_preferred=True
    )
    return institution


@pytest.fixture()
def institution_primary_type_1():
    institution = InstitutionFactory()
    institution._id = 'brown'
    institution.save()
    return institution


@pytest.fixture()
def institution_secondary_type_1():
    institution = InstitutionFactory()
    institution._id = 'thepolicylab'
    institution.save()
    return institution


@pytest.fixture()
def institution_primary_type_2():
    institution = InstitutionFactory()
    institution._id = 'fsu'
    institution.save()
    return institution


@pytest.fixture()
def institution_secondary_type_2():
    institution = InstitutionFactory()
    institution._id = 'nationalmaglab'
    institution.save()
    return institution


@pytest.fixture()
def institution_selective_type_1():
    institution = InstitutionFactory()
    institution._id = 'uom'
    institution.save()
    return institution


@pytest.fixture()
def institution_selective_type_2():
    institution = InstitutionFactory()
    institution._id = 'yls'
    institution.save()
    return institution


@pytest.fixture()
def url_auth_institution():
    return f'/{API_BASE}institutions/auth/'


@pytest.fixture()
def type_2_eligible_user_roles():
    return 'FSU_IAM_AD_MGMT;FSU_MYFSUADMIN;CS_ADMN_STDT_CNT;FSU_IAM_REG;FSU_OSF_MAGLAB;' \
           'FSU_FULL_IAM_LOOKUP;FSU_OB_Related_Content_FDA;FSU_OB_FI_EVERYONE;FSU_MS_LIC_FULL'


@pytest.fixture()
def type_2_ineligible_user_roles():
    return 'IT_Professional;FSU_IAM_AD_MGMT;FSU_MYFSUADMIN;CS_ADMN_STDT_CNT;FSU_IAM_REG;' \
           'FSU_FULL_IAM_LOOKUP;FSU_OB_Related_Content_FDA;FSU_OB_FI_EVERYONE;FSU_MS_LIC_FULL'


@pytest.mark.django_db
class TestInstitutionAuth:

    def test_invalid_payload(self, app, url_auth_institution):
        res = app.post(url_auth_institution, 'INVALID_PAYLOAD', expect_errors=True)
        assert res.status_code == 403

    def test_new_user_created(self, app, url_auth_institution, institution):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution in user.get_affiliated_institutions()

    def test_existing_user_found_but_not_affiliated(self, app, institution, url_auth_institution):

        username = 'user_not_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution in user.get_affiliated_institutions()

    def test_user_found_and_affiliated(self, app, institution, url_auth_institution):

        username = 'user_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution)
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == 1

    def test_new_user_names_not_provided(self, app, institution, url_auth_institution):

        username = 'user_created_without_names@osf.edu'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, fullname=''),
            expect_errors=True
        )
        assert res.status_code == 403

        user = OSFUser.objects.filter(username=username).first()
        assert not user

    def test_new_user_names_guessed_if_not_provided(self, app, institution, url_auth_institution):

        username = 'user_created_with_fullname_only@osf.edu'
        res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        # Given name and family name are guessed from full name
        assert user.given_name == 'Fake'
        assert user.family_name == 'User'

    def test_new_user_names_used_when_provided(self, app, institution, url_auth_institution):

        username = 'user_created_with_names@osf.edu'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, given_name='Foo', family_name='Bar')
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        # Given name and family name are set instead of guessed
        assert user.given_name == 'Foo'
        assert user.family_name == 'Bar'

    def test_user_active(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_active@user.edu', 'Foo Bar', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User',
                    department='Fake Department',
                )
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User names remains untouched
        assert user.fullname == fullname
        assert user.family_name == 'Bar'
        assert user.given_name == 'Foo'
        affiliation = user.get_institution_affiliation(institution._id)
        assert affiliation.sso_department == 'Fake Department'
        # Existing active user keeps their password
        assert user.has_usable_password()
        assert user.check_password(password)
        # Confirm affiliation
        assert institution in user.get_affiliated_institutions()

    def test_user_unclaimed(self, app, institution, url_auth_institution):

        username, fullname = 'user_nclaimed@user.edu', 'Foo Bar'
        project = ProjectFactory()
        user = project.add_unregistered_contributor(
            fullname=fullname,
            email=username,
            auth=Auth(project.creator)
        )
        user.save()
        # Unclaimed user is given an unusable password when being added as a contributor
        assert not user.has_usable_password()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User',
                    department='Fake Department',
                )
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and all names are updated
        assert user.is_active
        assert user.fullname == 'Fake User'
        assert user.family_name == 'User'
        assert user.given_name == 'Fake'
        affiliation = user.get_institution_affiliation(institution._id)
        assert affiliation.sso_department == 'Fake Department'
        # Unclaimed records must have been cleared
        assert not user.unclaimed_records
        # Previously unclaimed user must be assigned a usable password during institution auth
        assert user.has_usable_password()
        # User remains to be a contributor of the project
        assert project.is_contributor(user)
        # Confirm affiliation
        assert institution in user.get_affiliated_institutions()

    def test_user_unconfirmed(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_unconfirmed@osf.edu', 'Foo Bar', 'FuAsKeEr'
        user = OSFUser.create_unconfirmed(username, password, fullname)
        user.save()
        # Unconfirmed user has a usable password created during sign-up
        assert user.has_usable_password()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                )
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and all names are updated
        assert user.is_active
        assert user.fullname == 'Fake User'
        assert user.family_name == 'User'
        assert user.given_name == 'Fake'
        # Pending email verifications must be cleared
        assert not user.email_verifications
        # Previously unconfirmed user must be given a new password during institution auth
        assert user.has_usable_password()
        assert not user.check_password(password)
        # Confirm affiliation
        assert institution in user.get_affiliated_institutions()

    def test_user_inactive(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_inactive@osf.edu', 'Foo Bar', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        # User must be saved before deactivation
        user.save()
        user.deactivate_account()
        user.save()
        # Disabled user still has the original usable password
        assert user.has_usable_password()
        assert user.check_password(password)

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                ),
                expect_errors=True
            )
        assert res.status_code == 403
        assert not mock_signals.signals_sent()

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # Inactive user remains untouched, including affiliation
        assert user.is_disabled
        assert user.fullname == fullname
        assert user.given_name == 'Foo'
        assert user.family_name == 'Bar'
        assert institution not in user.get_affiliated_institutions()

    def test_user_external_unconfirmed(self, app, institution, url_auth_institution):

        # Create an unconfirmed user with pending external identity
        username, fullname = 'user_external_unconfirmed@osf.edu', 'Foo Bar'
        external_id_provider, external_id, status = 'ORCID', '1234-1234-1234-1234', 'CREATE'
        external_identity = {external_id_provider: {external_id: status}}
        accepted_terms_of_service = timezone.now()
        user = OSFUser.create_unconfirmed(
            username=username,
            password=None,
            fullname=fullname,
            external_identity=external_identity,
            campaign=None,
            accepted_terms_of_service=accepted_terms_of_service
        )
        user.save()
        assert not user.has_usable_password()
        assert user.external_identity

        # Send confirm email in order to add new email verifications
        send_confirm_email_async(
            user,
            user.username,
            external_id_provider=external_id_provider,
            external_id=external_id
        )
        user.save()
        assert user.email_verifications
        email_verifications = user.email_verifications

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User',
                    department='Fake User',
                ),
                expect_errors=True
            )
        assert res.status_code == 403
        assert not mock_signals.signals_sent()

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User remains untouched, including affiliation, external identity email verifcaitons
        assert user.fullname == fullname
        assert user.given_name == 'Foo'
        assert user.family_name == 'Bar'
        assert institution not in user.get_affiliated_institutions()
        assert external_identity == user.external_identity
        assert email_verifications == user.email_verifications
        assert accepted_terms_of_service == user.accepted_terms_of_service
        assert not user.has_usable_password()


@pytest.mark.django_db
class TestInstitutionStorageRegion:

    def test_region_updated_for_new_user(self, app, institution_region_preferred, institution_without_user_default_region, url_auth_institution):
        username = 'user_with_region_1@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0
        res = app.post(url_auth_institution, make_payload(institution_without_user_default_region, username))
        assert res.status_code == 204
        user = OSFUser.objects.get(username=username)
        assert user.addons_osfstorage_user_settings.default_region == institution_region_preferred

    def test_region_not_updated_for_new_user(self, app, user_default_region, institution_region_preferred, institution_with_default_user_region, url_auth_institution):
        username = 'user_with_region_2@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0
        res = app.post(url_auth_institution, make_payload(institution_with_default_user_region, username))
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user.addons_osfstorage_user_settings.default_region == user_default_region
        assert user.addons_osfstorage_user_settings.default_region != institution_region_preferred

    def test_region_not_updated_for_existing_user_affiliated(self, app, institution_region, institution_region_preferred,
                                                             institution_without_user_default_region, url_auth_institution):
        username = 'user_with_region_3@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.save()
        res = app.post(url_auth_institution, make_payload(institution_without_user_default_region, username))
        assert res.status_code == 204
        user.reload()
        assert user.addons_osfstorage_user_settings.default_region != institution_region
        assert user.addons_osfstorage_user_settings.default_region != institution_region_preferred

    def test_region_not_updated_for_existing_user_not_affiliated(self, app, institution_region, institution_region_preferred,
                                                                 institution_without_user_default_region, url_auth_institution):
        username = 'user_with_region_4@osf.edu'
        user = make_user(username, 'Bar Foo')
        user.add_or_update_affiliated_institution(institution_without_user_default_region)
        user.save()
        res = app.post(url_auth_institution, make_payload(institution_without_user_default_region, username))
        assert res.status_code == 204
        user.reload()
        assert user.addons_osfstorage_user_settings.default_region != institution_region
        assert user.addons_osfstorage_user_settings.default_region != institution_region_preferred


@pytest.mark.django_db
class TestInstitutionAuthnSharedSSOCriteriaType2:

    def test_new_user_primary_only(self, app, url_auth_institution, type_2_ineligible_user_roles,
                                   institution_primary_type_2, institution_secondary_type_2):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_ineligible_user_roles)
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()

    def test_new_user_primary_and_secondary(self, app, url_auth_institution, type_2_eligible_user_roles,
                                            institution_primary_type_2, institution_secondary_type_2):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 in user.get_affiliated_institutions()

    def test_existing_user_primary_only_not_affiliated(self, app, url_auth_institution, type_2_ineligible_user_roles,
                                                       institution_primary_type_2, institution_secondary_type_2):
        username = 'user_not_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_ineligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 1
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()

    def test_existing_user_primary_only_affiliated(self, app, url_auth_institution, type_2_ineligible_user_roles,
                                                   institution_primary_type_2, institution_secondary_type_2):
        username = 'user_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_ineligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()

    def test_existing_user_both_not_affiliated(self, app, url_auth_institution, type_2_eligible_user_roles,
                                               institution_primary_type_2, institution_secondary_type_2):

        username = 'user_both_not_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 2
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 in user.get_affiliated_institutions()

    def test_existing_user_both_affiliated(self, app, url_auth_institution, type_2_eligible_user_roles,
                                           institution_primary_type_2, institution_secondary_type_2):

        username = 'user_both_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.add_or_update_affiliated_institution(institution_secondary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 in user.get_affiliated_institutions()

    def test_existing_user_secondary_not_affiliated(self, app, url_auth_institution, type_2_eligible_user_roles,
                                                    institution_primary_type_2, institution_secondary_type_2):

        username = 'user_secondary_not@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 1
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 in user.get_affiliated_institutions()

    def test_invalid_criteria_action(self, app, url_auth_institution, type_2_eligible_user_roles,
                                     institution_primary_type_2, institution_secondary_type_2):

        INSTITUTION_SHARED_SSO_MAP.update({
            'fsu': {
                'attribute_name': 'userRoles',
                'criteria_action': 'invalid_criteria_action',
                'criteria_value': 'FSU_OSF_MAGLAB',
                'institution_id': 'nationalmaglab',
            },
        })

        username = 'user_invalid_criteria_action@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()

    def test_invalid_institution_id(self, app, url_auth_institution, type_2_eligible_user_roles,
                                    institution_primary_type_2, institution_secondary_type_2):

        INSTITUTION_SHARED_SSO_MAP.update({
            'fsu': {
                'attribute_name': 'userRoles',
                'criteria_action': SsoFilterCriteriaAction.CONTAINS.value,
                'criteria_value': 'FSU_OSF_MAGLAB',
                'institution_id': 'invalid_institution_id',
            },
        })

        username = 'user_invalid_institution_id@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles=type_2_eligible_user_roles)
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()

    def test_empty_criteria_value(self, app, url_auth_institution,
                                  institution_primary_type_2, institution_secondary_type_2):

        INSTITUTION_SHARED_SSO_MAP.update({
            'fsu': {
                'attribute_name': 'userRoles',
                'criteria_action': SsoFilterCriteriaAction.CONTAINS.value,
                'criteria_value': 'FSU_OSF_MAGLAB',
                'institution_id': 'nationalmaglab',
            },
        })

        username = 'user_invalid_criteria_value@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_2, username, user_roles='')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_2 in user.get_affiliated_institutions()
        assert institution_secondary_type_2 not in user.get_affiliated_institutions()


@pytest.mark.django_db
class TestInstitutionAuthnSharedSSOCriteriaType1:

    def test_new_user_primary_only(self, app, url_auth_institution,
                                   institution_primary_type_1, institution_secondary_type_1):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution_primary_type_1, username))
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()

    def test_new_user_primary_and_secondary(self, app, url_auth_institution,
                                            institution_primary_type_1, institution_secondary_type_1):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 in user.get_affiliated_institutions()

    def test_existing_user_primary_only_not_affiliated(self, app, url_auth_institution,
                                                       institution_primary_type_1, institution_secondary_type_1):
        username = 'user_not_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution_primary_type_1, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 1
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()

    def test_existing_user_primary_only_affiliated(self, app, url_auth_institution,
                                                   institution_primary_type_1, institution_secondary_type_1):
        username = 'user_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution_primary_type_1, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()

    def test_existing_user_both_not_affiliated(self, app, url_auth_institution,
                                               institution_primary_type_1, institution_secondary_type_1):

        username = 'user_both_not_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 2
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 in user.get_affiliated_institutions()

    def test_existing_user_both_affiliated(self, app, url_auth_institution,
                                           institution_primary_type_1, institution_secondary_type_1):

        username = 'user_both_affiliated@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.add_or_update_affiliated_institution(institution_secondary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 in user.get_affiliated_institutions()

    def test_existing_user_secondary_not_affiliated(self, app, url_auth_institution,
                                                    institution_primary_type_1, institution_secondary_type_1):

        username = 'user_secondary_not@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations + 1
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 in user.get_affiliated_institutions()

    def test_invalid_criteria_action(self, app, url_auth_institution,
                                     institution_primary_type_1, institution_secondary_type_1):

        INSTITUTION_SHARED_SSO_MAP.update({
            'brown': {
                'attribute_name': 'isMemberOf',
                'criteria_action': 'invalid_criteria_action',
                'criteria_value': 'thepolicylab',
                'institution_id': 'thepolicylab',
            },
        })

        username = 'user_invalid_criteria_action@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()

    def test_invalid_institution_id(self, app, url_auth_institution,
                                    institution_primary_type_1, institution_secondary_type_1):

        INSTITUTION_SHARED_SSO_MAP.update({
            'brown': {
                'attribute_name': 'isMemberOf',
                'criteria_action': SsoFilterCriteriaAction.EQUALS_TO.value,
                'criteria_value': 'thepolicylab',
                'institution_id': 'invalid_institution_id',
            },
        })

        username = 'user_invalid_institution_id@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='thepolicylab')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()

    def test_invalid_criteria_value(self, app, url_auth_institution,
                                    institution_primary_type_1, institution_secondary_type_1):

        INSTITUTION_SHARED_SSO_MAP.update({
            'brown': {
                'attribute_name': 'isMemberOf',
                'criteria_action': SsoFilterCriteriaAction.EQUALS_TO.value,
                'criteria_value': 'thepolicylab',
                'institution_id': 'thepolicylab',
            },
        })

        username = 'user_invalid_criteria_value@primary.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_primary_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution_primary_type_1, username, is_member_of='invalid_criteria_value')
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.get_affiliated_institutions().count() == number_of_affiliations
        assert institution_primary_type_1 in user.get_affiliated_institutions()
        assert institution_secondary_type_1 not in user.get_affiliated_institutions()


@pytest.mark.django_db
class TestInstitutionAuthnSelectiveSSOCriteriaType1:

    def test_selective_sso_allowed_new_user(self, app, url_auth_institution, institution_selective_type_1):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(
            institution_selective_type_1,
            username,
            selective_sso_filter='http://directory.manchester.ac.uk/epe/3rdparty/osf'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_selective_type_1 in user.get_affiliated_institutions()

    def test_selective_sso_allowed_existing_user_not_affiliated(self, app, url_auth_institution, institution_selective_type_1):

        username = 'user_not_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.save()

        payload = make_payload(
            institution_selective_type_1,
            username,
            selective_sso_filter='http://directory.manchester.ac.uk/epe/3rdparty/osf'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution_selective_type_1 in user.get_affiliated_institutions()

    def test_selective_sso_allowed_existing_user_affiliated(self, app, url_auth_institution, institution_selective_type_1):

        username = 'user_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_selective_type_1)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        payload = make_payload(
            institution_selective_type_1,
            username,
            selective_sso_filter='http://directory.manchester.ac.uk/epe/3rdparty/osf'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution_selective_type_1 in user.get_affiliated_institutions()
        assert number_of_affiliations == user.get_affiliated_institutions().count()

    def test_selective_sso_denied_empty_filter(self, app, url_auth_institution, institution_selective_type_1):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(institution_selective_type_1, username, selective_sso_filter='')
        res = app.post(url_auth_institution, payload, expect_errors=True)
        assert res.status_code == 403
        assert {'detail': 'InstitutionSsoSelectiveLoginDenied'} in res.json['errors']

    def test_selective_sso_denied_invalid_filter(self, app, url_auth_institution, institution_selective_type_1):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(institution_selective_type_1, username, selective_sso_filter='invalid_non_empty_filter')
        res = app.post(url_auth_institution, payload, expect_errors=True)
        assert res.status_code == 403
        assert {'detail': 'InstitutionSsoSelectiveLoginDenied'} in res.json['errors']


@pytest.mark.django_db
class TestInstitutionAuthnSelectiveSSOCriteriaType2:

    def test_selective_sso_allowed_new_user(self, app, url_auth_institution, institution_selective_type_2):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(
            institution_selective_type_2,
            username,
            selective_sso_filter='Yes'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is None
        assert institution_selective_type_2 in user.get_affiliated_institutions()

    def test_selective_sso_allowed_existing_user_not_affiliated(self, app, url_auth_institution, institution_selective_type_2):

        username = 'user_not_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.save()

        payload = make_payload(
            institution_selective_type_2,
            username,
            selective_sso_filter='yes'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution_selective_type_2 in user.get_affiliated_institutions()

    def test_selective_sso_allowed_existing_user_affiliated(self, app, url_auth_institution, institution_selective_type_2):

        username = 'user_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.add_or_update_affiliated_institution(institution_selective_type_2)
        user.save()
        number_of_affiliations = user.get_affiliated_institutions().count()

        payload = make_payload(
            institution_selective_type_2,
            username,
            selective_sso_filter='y'
        )
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution_selective_type_2 in user.get_affiliated_institutions()
        assert number_of_affiliations == user.get_affiliated_institutions().count()

    def test_selective_sso_denied_empty_filter(self, app, url_auth_institution, institution_selective_type_2):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(institution_selective_type_2, username, selective_sso_filter='')
        res = app.post(url_auth_institution, payload, expect_errors=True)
        assert res.status_code == 403
        assert {'detail': 'InstitutionSsoSelectiveLoginDenied'} in res.json['errors']

    def test_selective_sso_denied_invalid_filter(self, app, url_auth_institution, institution_selective_type_2):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        payload = make_payload(institution_selective_type_2, username, selective_sso_filter='invalid_non_empty_filter')
        res = app.post(url_auth_institution, payload, expect_errors=True)
        assert res.status_code == 403
        assert {'detail': 'InstitutionSsoSelectiveLoginDenied'} in res.json['errors']


@pytest.mark.django_db
class TestInstitutionAuthnWithIdentity:

    def test_new_user(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_1@osf.edu'
        sso_identity = 'osf_user_1'
        department = 'osf_team_1'
        assert get_user(email=sso_email) is None

        payload = make_payload(institution, sso_email, sso_identity=sso_identity, department=department)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user = OSFUser.objects.get(username=sso_email)
        assert user
        assert user.fullname == 'Fake User'
        assert user.is_active
        assert user.accepted_terms_of_service is None
        assert user.is_affiliated_with_institution(institution)

        affiliation = InstitutionAffiliation.objects.get(user__id=user.id, institution__id=institution.id)
        assert affiliation
        assert affiliation.sso_mail == sso_email
        assert affiliation.sso_identity == sso_identity
        assert affiliation.sso_department == department

    def test_existing_user_by_both_email_and_identity(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_2@osf.edu'
        sso_identity = 'osf_user_2'
        department = 'osf_team_2'

        assert get_user(email=sso_email) is None
        user = make_user(sso_email, 'User2 OSF')
        user.save()

        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_identity=sso_identity, sso_mail=sso_email)
        assert affiliation
        assert affiliation.sso_identity == sso_identity
        assert affiliation.sso_mail == sso_email
        assert affiliation.sso_department is None
        assert user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity, department=department)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User2 OSF'
        assert user.is_affiliated_with_institution(institution)
        affiliation.reload()
        assert affiliation.sso_department == department

    def test_existing_user_by_email_without_identity(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_3@osf.edu'
        assert get_user(email=sso_email) is None

        user = make_user(sso_email, 'User3 OSF')
        user.save()

        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_mail=sso_email)
        assert affiliation
        assert affiliation.sso_identity is None
        assert user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User3 OSF'
        assert user.is_affiliated_with_institution(institution)
        affiliation.reload()
        assert affiliation.sso_identity is None

    def test_existing_user_by_email_with_identity_to_add(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_4@osf.edu'
        sso_identity = 'osf_user_4'

        assert get_user(email=sso_email) is None
        user = make_user(sso_email, 'User4 OSF')
        user.save()

        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_mail=sso_email)
        assert affiliation
        assert affiliation.sso_identity is None
        assert user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User4 OSF'
        assert user.is_affiliated_with_institution(institution)
        affiliation.reload()
        assert affiliation.sso_identity == sso_identity

    def test_existing_user_by_identity_with_email_to_add(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_5_alt@osf.edu'
        sso_identity = 'osf_user_5'

        assert get_user(email=sso_email) is None
        username = 'osf_user_5@osf.io'
        user = make_user(username, 'User5 OSF')
        user.save()

        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_identity=sso_identity)
        assert affiliation
        assert affiliation.sso_mail is None
        assert user.is_affiliated_with_institution(institution)
        assert sso_email not in user.emails.values_list('address', flat=True)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User5 OSF'
        assert sso_email in user.emails.values_list('address', flat=True)
        assert user.is_affiliated_with_institution(institution)
        affiliation.reload()
        assert affiliation.sso_mail == sso_email

    def test_different_user_by_email_and_by_identity(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_6_alt@osf.edu'
        assert get_user(email=sso_email) is None
        user_by_email = make_user(sso_email, 'User6 OSF Alt')
        user_by_email.save()

        username = 'osf_user_6@osf.io'
        sso_identity = 'osf_user_6'
        assert get_user(email=username) is None
        user_by_identity = make_user(username, 'User6 OSF')
        user_by_identity.save()

        assert not user_by_email.is_affiliated_with_institution(institution)
        assert not user_by_identity.is_affiliated_with_institution(institution)
        affiliation_old = user_by_identity.add_or_update_affiliated_institution(institution, sso_identity=sso_identity)
        assert affiliation_old
        assert affiliation_old.sso_identity == sso_identity
        assert user_by_identity.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user_by_email.reload()
        assert user_by_email.fullname == 'User6 OSF Alt'
        user_by_identity.reload()
        assert user_by_identity.fullname == 'User6 OSF'

        affiliation_old.reload()
        assert user_by_identity.is_affiliated_with_institution(institution)
        assert affiliation_old.sso_identity is None

        assert user_by_email.is_affiliated_with_institution(institution)
        affiliation_new = user_by_email.get_institution_affiliation(institution._id)
        assert affiliation_new
        assert affiliation_new.sso_mail == sso_email
        assert affiliation_new.sso_identity == sso_identity

    def test_duplicate_identity_exception(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_7_alt@osf.edu'
        sso_identity = 'osf_user_7'
        assert get_user(email=sso_email) is None
        user_by_email = make_user(sso_email, 'User7 OSF Alt')
        user_by_email.save()
        assert not user_by_email.is_affiliated_with_institution(institution)
        affiliation_1 = user_by_email.add_or_update_affiliated_institution(institution, sso_identity=sso_identity)
        assert affiliation_1
        assert affiliation_1.sso_identity == sso_identity
        assert user_by_email.is_affiliated_with_institution(institution)

        username = 'osf_user_7@osf.io'
        assert get_user(email=username) is None
        user_by_identity = make_user(username, 'User7 OSF')
        user_by_identity.save()
        assert not user_by_identity.is_affiliated_with_institution(institution)
        affiliation_2 = user_by_identity.add_or_update_affiliated_institution(institution, sso_identity=sso_identity)
        assert affiliation_2
        assert affiliation_2.sso_identity == sso_identity
        assert user_by_identity.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        res = app.post(url_auth_institution, payload, expect_errors=True)
        assert res.status_code == 403
        assert {'detail': 'InstitutionSsoDuplicateIdentity'} in res.json['errors']

    def test_blank_identity_existing_affiliation(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_8@osf.edu'
        sso_identity = '        '
        assert get_user(email=sso_email) is None
        user = make_user(sso_email, 'User8 OSF')
        user.save()

        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_mail=sso_email)
        assert affiliation
        assert affiliation.sso_identity is None
        assert user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User8 OSF'
        affiliation.reload()
        assert affiliation.sso_identity is None

    def test_empty_identity_new_affiliation(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_9@osf.edu'
        sso_identity = ''
        assert get_user(email=sso_email) is None
        user = make_user(sso_email, 'User9 OSF')
        user.save()
        assert not user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'User9 OSF'
        assert user.is_affiliated_with_institution(institution)

        affiliation = user.get_institution_affiliation(institution._id)
        assert affiliation
        assert affiliation.sso_mail == sso_email
        assert affiliation.sso_identity is None

    def test_identity_not_available(self, app, url_auth_institution, institution):

        sso_email = 'osf_user_10_alt@osf.edu'
        fullname = 'User10 OSF Alt'
        assert get_user(email=sso_email) is None

        username = 'osf_user_10@osf.io'
        sso_identity = InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE
        assert get_user(email=username) is None
        user = make_user(username, 'User10 OSF')
        user.save()
        assert not user.is_affiliated_with_institution(institution)
        affiliation = user.add_or_update_affiliated_institution(institution, sso_identity=sso_identity)
        assert affiliation
        assert affiliation.sso_identity == InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE
        assert user.is_affiliated_with_institution(institution)

        payload = make_payload(institution, sso_email, sso_identity=sso_identity, fullname=fullname)
        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, payload)
        assert res.status_code == 204
        assert mock_signals.signals_sent() == {signals.user_confirmed}

        user.reload()
        assert user.fullname == 'User10 OSF'
        assert user.is_affiliated_with_institution(institution)
        assert sso_email not in user.emails.values_list('address', flat=True)
        affiliation.reload()
        assert affiliation.sso_mail is None
        assert affiliation.sso_identity == InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE

        new_user = OSFUser.objects.get(username=sso_email)
        assert new_user
        assert new_user.fullname == fullname
        assert new_user.is_active
        assert new_user.accepted_terms_of_service is None
        assert new_user.is_affiliated_with_institution(institution)

        new_affiliation = InstitutionAffiliation.objects.get(user__id=new_user.id, institution__id=institution.id)
        assert new_affiliation
        assert new_affiliation.sso_mail == sso_email
        assert new_affiliation.sso_identity is None
