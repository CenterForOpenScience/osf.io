import json
import mock
import jwe
import jwt
import pytest
from api.base import settings
from api.base.settings.defaults import API_BASE
from osf.models import OSFUser
from osf_tests.factories import InstitutionFactory, UserFactory
from tests.json_api_test_app import JSONAPITestApp


def make_user(username, fullname):
    return UserFactory(username=username, fullname=fullname)


def make_payload(
        institution,
        username,
        fullname='Fake User',
        given_name='',
        family_name='',
        middle_names='',
        department='',
        jaGivenName='',
        jaSurname='',
        jaFullname='',
        jaDisplayName='',
        jaMiddleNames='',
        jaOrganizationalUnitName='',
        organizationalUnit='',
        organizationName='',

):
    data = {
        'provider': {
            'id': institution._id,
            'idp': '',
            'user': {
                'middleNames': middle_names,
                'familyName': family_name,
                'givenName': given_name,
                'fullname': fullname,
                'suffix': '',
                'username': username,
                'department': department,

                'jaGivenName': jaGivenName,
                'jaSurname': jaSurname,
                'jaDisplayName': jaDisplayName,
                'jaFullname': jaFullname,
                'jaMiddleNames': jaMiddleNames,
                'jaOrganizationalUnitName': jaOrganizationalUnitName,
                'organizationalUnitName': organizationalUnit,
                'organizationName': organizationName,
            }
        }
    }

    return jwe.encrypt(
        jwt.encode(
            {
                'sub': username,
                'data': json.dumps(data)
            },
            settings.JWT_SECRET,
            algorithm='HS256'
        ),
        settings.JWE_SECRET
    )


@pytest.fixture()
def app():
    return JSONAPITestApp()


@pytest.mark.django_db
class TestInstitutionAuth:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_auth_institution(self):
        return '/{0}institutions/auth/'.format(API_BASE)

    def test_authenticate_jaSurname_and_jaGivenName_are_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        jagivenname = 'given'
        jasurname = 'sur'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username,
                         jaGivenName=jagivenname, jaSurname=jasurname),
            expect_errors=True
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.ext.data['idp_attr']['fullname_ja'] == jagivenname + ' ' + jasurname

    def test_authenticate_jaGivenName_is_valid(
            self, app, institution, url_auth_institution):
        username = 'user@gmail.com'
        jagivenname = 'givenname'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, jaGivenName=jagivenname),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.given_name_ja == jagivenname

    def test_authenticate_jaSurname_is_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        jasurname = 'surname'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, jaSurname=jasurname),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.family_name_ja == jasurname

    def test_authenticate_jaMiddleNames_is_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        middlename = 'surname'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, jaMiddleNames=middlename),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.middle_names_ja == middlename

    def test_authenticate_givenname_is_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        given_name = 'givenname'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, given_name=given_name),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.given_name == given_name

    def test_authenticate_familyname_is_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        family_name = 'familyname'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, family_name=family_name),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.family_name == family_name

    def test_authenticate_middlename_is_valid(
            self, app, institution, url_auth_institution):

        username = 'user@gmail.com'
        middle_names = 'middlenames'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, middle_names=middle_names),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.middle_names == middle_names

    @mock.patch('api.institutions.authentication.login_by_eppn')
    def test_authenticate_jaOrganizationalUnitName_is_valid(
            self, mock, app, institution, url_auth_institution):
        mock.return_value = True
        username = 'user@gmail.com'
        jaorganizationname = 'organizationname'
        organizationname = 'name'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username,
                         jaOrganizationalUnitName=jaorganizationname,
                         organizationName=organizationname),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username='tmp_eppn_' + username).first()
        assert user
        assert user.jobs[0]['department_ja'] == jaorganizationname

    @mock.patch('api.institutions.authentication.login_by_eppn')
    def test_authenticate_OrganizationalUnitName_is_valid(
            self, mock, app, institution, url_auth_institution):
        mock.return_value = True
        username = 'user@gmail.com'
        organizationnameunit = 'organizationname'
        organizationname = 'name'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username,
                         organizationalUnit=organizationnameunit,
                         organizationName=organizationname),
            expect_errors=True
        )
        assert res.status_code == 204
        user = OSFUser.objects.filter(username='tmp_eppn_' + username).first()
        assert user
        assert user.jobs[0]['department'] == organizationnameunit
