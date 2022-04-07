from __future__ import absolute_import
import pytest
import mock
from nose.tools import assert_equal
from osf.models import OSFUser
from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, InstitutionFactory

pytestmark = pytest.mark.django_db


class TestPropertyIsFullAccountRequiredInfo(OsfTestCase):

    def setUp(self):
        super(TestPropertyIsFullAccountRequiredInfo, self).setUp()

    def test_is_full_account_required_info_miss_institution(self):
        user_auth = AuthUserFactory()
        assert_equal(user_auth.is_full_account_required_info, True)

    def test_is_full_account_required_info_miss_jobs(self):
        user_auth = AuthUserFactory()
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        assert_equal(user_auth.is_full_account_required_info, False)

    def test_is_full_account_required_info_has_jobs(self):
        name = 'name'
        user_auth = AuthUserFactory(fullname=name)
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        user_auth.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1980',
            'institution_ja': 'Organization JP'
        }]

        user_auth.save()
        user = OSFUser.objects.filter(fullname=name).first()
        assert user
        assert user.jobs
        assert_equal(user_auth.is_full_account_required_info, False)

    @mock.patch('osf.models.user.OSFUser.ext', new_callable=mock.PropertyMock)
    def test_is_full_account_required_info_exception(self, mock_idp_attr):
        family_name_en = 'family name en'
        family_name_ja = 'family name ja'
        given_name_en = 'given_name en'
        given_name_ja = 'given_name ja'
        user_auth = AuthUserFactory()
        user_auth.family_name = family_name_en
        user_auth.family_name_ja = family_name_ja
        user_auth.given_name = given_name_en
        user_auth.given_name_ja = given_name_ja
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        user_auth.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1980',
            'institution_ja': 'Organization JP'
        }]
        user_auth.save()
        mock_idp_attr.side_effect = AttributeError('exception')
        assert_equal(user_auth.is_full_account_required_info, True)
