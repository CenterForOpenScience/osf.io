import json
import jwe
import jwt

import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts

from api.base import settings
from api.base.settings.defaults import API_BASE
from osf.models import OSFUser, UserExtendedData
from website.util import api_url_for
from framework.auth import Auth
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)


# tests for InstitutionAuthentication.
# get Shibboleth attribute via cas
# refer to api_tests/institutions/views/test_institution_auth.py

TMP_EPPN_PREFIX = 'tmp_eppn_'

def make_payload(
        institution, eppn, fullname,
        given_name='', family_name='',
        entitlement='',
        email='', organization_name='',
        organizational_unit=''
):
    data = {
        'provider': {
            'idp': institution.email_domains,
            'id': institution._id,
            'user': {
                'middleNames': '',
                'familyName': family_name,
                'givenName': given_name,
                'fullname': fullname,
                'suffix': '',
                'username': eppn,
                'entitlement':  entitlement,
                'email': email,
                'organizationName': organization_name,
                'organizationalUnitName': organizational_unit,
                'jaDisplayName': '',  # jaDisplayName
                'jaSurname': family_name + '_ja',  # jasn
                'jaGivenName': given_name + '_ja',  # jaGivenName
                'jaMiddleNames': '',
                'jaOrganizationName': organization_name + '_ja',  # jao
                'jaOrganizationalUnitName': organizational_unit + '_ja',  # jaou
            }
        }
    }
    return jwe.encrypt(jwt.encode({
        'sub': eppn,
        'data': json.dumps(data)
    }, settings.JWT_SECRET, algorithm='HS256'), settings.JWE_SECRET)


@pytest.mark.django_db
class TestGettingShibbolethAttribute:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_auth_institution(self):
        return '/{0}institutions/auth/'.format(API_BASE)

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_without_email(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'
        tmp_eppn_username = TMP_EPPN_PREFIX + eppn

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name)
        )

        assert res.status_code == 204
        user = OSFUser.objects.get(username=tmp_eppn_username)
        assert user
        assert user.fullname == fullname
        assert user.eppn == eppn
        assert user.have_email == False
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_with_email(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'john.smith@circle.edu'
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name, email=email)
        )

        assert res.status_code == 204
        user = OSFUser.objects.get(username=email)
        assert user
        assert user.fullname == fullname
        assert user.eppn == eppn
        assert user.have_email == True
        assert user.emails.filter(address=email).exists()
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_with_email_and_profile_attr(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'john.smith@circle.edu'
        entitlement = 'GakuninRDMAdmin'
        organization_name = 'Example University'
        organization_name_ja = organization_name + '_ja'
        organizational_unit = 'Example Unit'
        organizational_unit_ja = organizational_unit + '_ja'

        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'
        expected_full_name_ja = given_name_ja + ' ' + family_name_ja

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname,
                given_name, family_name,
                entitlement=entitlement, email=email,
                organization_name=organization_name,
                organizational_unit=organizational_unit
            )
        )

        assert res.status_code == 204
        user = OSFUser.objects.get(username=email)
        assert user
        assert user.fullname == fullname
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja
        assert user.eppn == eppn
        assert user.have_email == True
        assert user.jobs[-1] == {
            'title': '',
            'institution_ja': organization_name_ja,
            'department_ja': organizational_unit_ja,
            'institution': organization_name,
            'department': organizational_unit,
            'location': '',
            'startMonth': '',
            'startYear': '',
            'endMonth': '',
            'endYear': '',
            'ongoing': False
        }

        idp_attr = user.ext.data['idp_attr']
        assert idp_attr
        assert idp_attr['fullname'] == fullname
        assert idp_attr['fullname_ja'] == expected_full_name_ja
        assert idp_attr['entitlement'] == entitlement
        assert user.is_staff == True
        assert idp_attr['email'] == email
        assert idp_attr['organization_name'] == organization_name
        assert idp_attr['organizational_unit'] == organizational_unit
        assert idp_attr['organization_name_ja'] == organization_name_ja
        assert idp_attr['organizational_unit_ja'] == organizational_unit_ja

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_with_email_and_profile_attr_without_orgname(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'john.smith@circle.edu'
        organizational_unit = 'Example Unit'
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name, email=email,
                organizational_unit=organizational_unit
            )
        )

        assert res.status_code == 204
        user = OSFUser.objects.get(username=email)
        assert user
        assert user.fullname == fullname
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja
        assert user.have_email == True
        assert not user.jobs
        assert not user.schools

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_with_blacklist_email(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'johon@example.com'
        tmp_eppn_username = TMP_EPPN_PREFIX + eppn
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'
        expected_full_name = given_name_ja + ' ' + family_name_ja

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name, email=email)
        )

        assert res.status_code == 204

        # email is ignored
        from django.core.exceptions import ObjectDoesNotExist
        with assert_raises(ObjectDoesNotExist):
            OSFUser.objects.get(username=eppn)

        user = OSFUser.objects.get(username=tmp_eppn_username)
        assert user
        assert user.fullname == fullname
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja
        assert user.eppn == eppn
        assert not user.emails.filter(address=email).exists()
        assert user.have_email == False

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_same_email_is_ignored(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'john.smith@circle.edu'
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name, email=email)
        )
        assert res.status_code == 204
        user = OSFUser.objects.get(username=email)
        assert user
        assert user.have_email == True

        eppn2 = 'jsmith2@circle.edu'  # another user
        tmp_eppn_username2 = TMP_EPPN_PREFIX + eppn2

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn2, fullname, given_name, family_name, email=email)
        )
        assert res.status_code == 204

        # same email is ignored
        user2 = OSFUser.objects.get(username=tmp_eppn_username2)
        assert user2
        assert user2.fullname == fullname  # same fullname is OK
        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja
        assert user2.eppn == eppn2
        assert not user2.emails.filter(address=email).exists()
        assert user2.have_email == False

    @mock.patch('api.institutions.authentication.settings.LOGIN_BY_EPPN', True)
    def test_existing_fullname_isnot_changed(self, app, institution, url_auth_institution):
        eppn = 'jsmith@circle.edu'
        fullname = 'John Smith'
        email = 'john.smith@circle.edu'
        given_name = 'John'
        given_name_ja = given_name + '_ja'
        family_name = 'Smitth'
        family_name_ja = family_name + '_ja'

        app.post(
            url_auth_institution,
            make_payload(institution, eppn, fullname, given_name, family_name, email=email)
        )

        new_fullname = 'New John Smith'
        new_email = 'new.john.smith@circle.edu'

        new_given_name = 'Bob'
        new_given_name_ja = new_given_name + '_ja'
        new_family_name = 'Wayne'
        new_family_name_ja = new_family_name + '_ja'
        new_expected_full_name_ja = new_given_name_ja + ' ' + new_family_name_ja

        res = app.post(
            url_auth_institution,
            make_payload(institution, eppn, new_fullname,
                         new_given_name, new_family_name, email=new_email)
        )

        # user.fullname is not changned
        assert res.status_code == 204
        user = OSFUser.objects.get(username=email)
        assert user
        assert user.fullname == fullname
        assert user.emails.filter(address=email).exists()
        assert not user.emails.filter(address=new_email).exists()

        assert user.given_name_ja == given_name_ja
        assert user.family_name_ja == family_name_ja

        # user.ext is changed
        idp_attr = user.ext.data['idp_attr']
        assert idp_attr
        assert idp_attr['fullname'] == new_fullname
        assert idp_attr['fullname_ja'] == new_expected_full_name_ja
        assert idp_attr['email'] == new_email


def set_user_extended_data(user):
    fullname = user.fullname
    entitlement = 'fake entitlement'
    email = user.username
    organization_name = 'fake o'
    organizational_unit = 'fake ou'
    ext = UserExtendedData(user=user)
    ext.data = {
        'idp_attr': {
            'fullname': fullname,
            'entitlement': entitlement,
            'email': email,
            'organization_name': organization_name,
            'organizational_unit': organizational_unit,
        }}
    ext.save()
    return (organization_name, organizational_unit)

# refer to tests/test_views.py
@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestUserProfile(OsfTestCase):

    def setUp(self):
        super(TestUserProfile, self).setUp()
        self.user = AuthUserFactory()

    def test_unserialize_and_serialize_jobs_with_idp_attr(self):
        jobs = [{
            'institution_ja': 'an institution' + '_ja',
            'department_ja': 'a department' + '_ja',
            'institution': 'an institution',
            'department': 'a department',
            'title': 'a title',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution_ja': 'another institution' + '_ja',
            'department_ja': None,
            'institution': 'another institution',
            'department': None,
            'title': None,
            'startMonth': 'May',
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        self.app.put_json(url, payload, auth=self.user.auth)

        organization_name, organizational_unit = set_user_extended_data(self.user)

        self.user.reload()
        assert_equal(len(self.user.jobs), 2)
        url = api_url_for('serialize_jobs')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(jobs):
            assert_equal(job, res.json['contents'][i])

        idp_attr = res.json['idp_attr']
        assert_equal(idp_attr['institution'], organization_name)
        assert_equal(idp_attr['department'], organizational_unit)

    def test_unserialize_and_serialize_schools_with_idp_attr(self):
        schools = [{
            'institution_ja': 'an institution' + '_ja',
            'department_ja': 'a department' + '_ja',
            'institution': 'an institution',
            'department': 'a department',
            'degree': 'a degree',
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution_ja': 'another institution' + '_ja',
            'department_ja': None,
            'institution': 'another institution',
            'department': None,
            'degree': None,
            'startMonth': 5,
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': schools}
        url = api_url_for('unserialize_schools')
        self.app.put_json(url, payload, auth=self.user.auth)

        organization_name, organizational_unit = set_user_extended_data(self.user)

        self.user.reload()
        assert_equal(len(self.user.schools), 2)
        url = api_url_for('serialize_schools')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(schools):
            assert_equal(job, res.json['contents'][i])

        idp_attr = res.json['idp_attr']
        assert_equal(idp_attr['institution'], organization_name)
        assert_equal(idp_attr['department'], organizational_unit)
