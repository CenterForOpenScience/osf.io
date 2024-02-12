from unittest import mock
import os
import pytest

from lxml import etree
from requests.models import Response

from framework.auth import tasks
from osf.models.institution import IntegrationType
from osf_tests.factories import UserFactory, InstitutionFactory
from tests.base import fake
from website.settings import ORCID_RECORD_EDUCATION_PATH, ORCID_RECORD_EMPLOYMENT_PATH


@pytest.mark.django_db
class TestInstitutionAffiliationViaOrcidSso:
    @pytest.fixture(autouse=True)
    def disable_sentry(self):
        with mock.patch('framework.sentry.enabled', False):
            yield

    @pytest.fixture()
    def response_content_educations(self):
        with open(os.path.join(os.path.dirname(__file__), 'education_affiliations.xml'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def response_content_employments(self):
        with open(os.path.join(os.path.dirname(__file__), 'employment_affiliations.xml'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def xml_data_educations(self, response_content_educations):
        return etree.XML(response_content_educations)

    @pytest.fixture()
    def xml_data_employments(self, response_content_employments):
        return etree.XML(response_content_employments)

    @pytest.fixture()
    def orcid_id_verified(self):
        return '1111-2222-3333-4444'

    @pytest.fixture()
    def orcid_id_link(self):
        return fake.ean()

    @pytest.fixture()
    def orcid_id_create(self):
        return fake.ean()

    @pytest.fixture()
    def orcid_id_random(self):
        return fake.ean()

    @pytest.fixture()
    def user_with_orcid_id_verified(self, orcid_id_verified):
        return UserFactory(external_identity={'ORCID': {orcid_id_verified: 'VERIFIED'}})

    @pytest.fixture()
    def user_with_orcid_id_link(self, orcid_id_link):
        return UserFactory(external_identity={'ORCID': {orcid_id_link: 'LINK'}})

    @pytest.fixture()
    def user_with_orcid_id_create(self, orcid_id_create):
        return UserFactory(external_identity={'ORCID': {orcid_id_create: 'CREATE'}})

    @pytest.fixture()
    def user_without_orcid_id(self):
        return UserFactory()

    @pytest.fixture()
    def eligible_institution(self):
        institution = InstitutionFactory()
        institution.delegation_protocol = IntegrationType.AFFILIATION_VIA_ORCID.value
        institution.orcid_record_verified_source = 'ORCID Integration at a Verified Institution'
        institution.save()
        return institution

    @pytest.fixture()
    def another_eligible_institution(self):
        institution = InstitutionFactory()
        institution.delegation_protocol = IntegrationType.AFFILIATION_VIA_ORCID.value
        institution.orcid_record_verified_source = 'ORCID Integration for another Verified Institution'
        institution.save()
        return institution

    @pytest.fixture()
    def user_verified_and_affiliated(self, orcid_id_verified, eligible_institution):
        user = UserFactory(external_identity={'ORCID': {orcid_id_verified: 'VERIFIED'}})
        user.add_or_update_affiliated_institution(eligible_institution)
        return user

    @mock.patch('framework.auth.tasks.check_institution_affiliation')
    @mock.patch('framework.auth.tasks.verify_user_orcid_id')
    def test_update_affiliation_for_orcid_sso_users_new_affiliation(
            self,
            mock_verify_user_orcid_id,
            mock_check_institution_affiliation,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_verify_user_orcid_id.return_value = True
        mock_check_institution_affiliation.return_value = eligible_institution
        assert eligible_institution not in user_with_orcid_id_verified.get_affiliated_institutions()
        tasks.update_affiliation_for_orcid_sso_users(user_with_orcid_id_verified._id, orcid_id_verified)
        assert eligible_institution in user_with_orcid_id_verified.get_affiliated_institutions()

    @mock.patch('framework.auth.tasks.check_institution_affiliation')
    @mock.patch('framework.auth.tasks.verify_user_orcid_id')
    def test_update_affiliation_for_orcid_sso_users_existing_affiliation(
            self,
            mock_verify_user_orcid_id,
            mock_check_institution_affiliation,
            user_verified_and_affiliated,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_verify_user_orcid_id.return_value = True
        mock_check_institution_affiliation.return_value = eligible_institution
        assert eligible_institution in user_verified_and_affiliated.get_affiliated_institutions()
        tasks.update_affiliation_for_orcid_sso_users(user_verified_and_affiliated._id, orcid_id_verified)
        assert eligible_institution in user_verified_and_affiliated.get_affiliated_institutions()

    @mock.patch('framework.auth.tasks.check_institution_affiliation')
    @mock.patch('framework.auth.tasks.verify_user_orcid_id')
    def test_update_affiliation_for_orcid_sso_users_verification_failed(
            self,
            mock_verify_user_orcid_id,
            mock_check_institution_affiliation,
            user_with_orcid_id_link,
            orcid_id_link,
            eligible_institution,
    ):
        mock_verify_user_orcid_id.return_value = False
        tasks.update_affiliation_for_orcid_sso_users(user_with_orcid_id_link._id, orcid_id_link)
        mock_check_institution_affiliation.assert_not_called()
        assert eligible_institution not in user_with_orcid_id_link.get_affiliated_institutions()

    @mock.patch('framework.auth.tasks.check_institution_affiliation')
    @mock.patch('framework.auth.tasks.verify_user_orcid_id')
    def test_update_affiliation_for_orcid_sso_users_institution_not_found(
            self,
            mock_verify_user_orcid_id,
            mock_check_institution_affiliation,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_verify_user_orcid_id.return_value = True
        mock_check_institution_affiliation.return_value = None
        assert eligible_institution not in user_with_orcid_id_verified.get_affiliated_institutions()
        tasks.update_affiliation_for_orcid_sso_users(user_with_orcid_id_verified._id, orcid_id_verified)
        assert eligible_institution not in user_with_orcid_id_verified.get_affiliated_institutions()

    def test_verify_user_orcid_id_verified(self, user_with_orcid_id_verified, orcid_id_verified):
        assert tasks.verify_user_orcid_id(user_with_orcid_id_verified, orcid_id_verified)

    def test_verify_user_orcid_id_link(self, user_with_orcid_id_link, orcid_id_link):
        assert not tasks.verify_user_orcid_id(user_with_orcid_id_link, orcid_id_link)

    def test_verify_user_orcid_id_create(self, user_with_orcid_id_create, orcid_id_create):
        assert not tasks.verify_user_orcid_id(user_with_orcid_id_create, orcid_id_create)

    def test_verify_user_orcid_id_none(self, user_without_orcid_id, orcid_id_random):
        assert not tasks.verify_user_orcid_id(user_without_orcid_id, orcid_id_random)

    @mock.patch('framework.auth.tasks.get_orcid_employment_sources')
    @mock.patch('framework.auth.tasks.get_orcid_education_sources')
    def test_check_institution_affiliation_from_employment_sources(
            self,
            mock_get_orcid_education_sources,
            mock_get_orcid_employment_sources,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_get_orcid_employment_sources.return_value = [
            eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.fullname,
        ]
        mock_get_orcid_education_sources.return_value = [user_with_orcid_id_verified.username, ]
        institution = tasks.check_institution_affiliation(orcid_id_verified)
        assert institution == eligible_institution

    @mock.patch('framework.auth.tasks.get_orcid_employment_sources')
    @mock.patch('framework.auth.tasks.get_orcid_education_sources')
    def test_check_institution_affiliation_from_education_sources(
            self,
            mock_get_orcid_education_sources,
            mock_get_orcid_employment_sources,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_get_orcid_employment_sources.return_value = [user_with_orcid_id_verified.fullname, ]
        mock_get_orcid_education_sources.return_value = [
            eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.username,
        ]
        institution = tasks.check_institution_affiliation(orcid_id_verified)
        assert institution == eligible_institution

    @mock.patch('framework.auth.tasks.get_orcid_employment_sources')
    @mock.patch('framework.auth.tasks.get_orcid_education_sources')
    def test_check_institution_affiliation_no_result(
            self,
            mock_get_orcid_education_sources,
            mock_get_orcid_employment_sources,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
    ):
        mock_get_orcid_employment_sources.return_value = [user_with_orcid_id_verified.fullname, ]
        mock_get_orcid_education_sources.return_value = [user_with_orcid_id_verified.username, ]
        institution = tasks.check_institution_affiliation(orcid_id_verified)
        assert institution is None

    @mock.patch('framework.auth.tasks.get_orcid_employment_sources')
    @mock.patch('framework.auth.tasks.get_orcid_education_sources')
    def test_check_institution_affiliation_multiple_results_case_1(
            self,
            mock_get_orcid_education_sources,
            mock_get_orcid_employment_sources,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
            another_eligible_institution,
    ):
        mock_get_orcid_employment_sources.return_value = [
            another_eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.fullname,
        ]
        mock_get_orcid_education_sources.return_value = [
            eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.username,
        ]
        institution = tasks.check_institution_affiliation(orcid_id_verified)
        assert institution == another_eligible_institution

    @mock.patch('framework.auth.tasks.get_orcid_employment_sources')
    @mock.patch('framework.auth.tasks.get_orcid_education_sources')
    def test_check_institution_affiliation_multiple_results_case_2(
            self,
            mock_get_orcid_education_sources,
            mock_get_orcid_employment_sources,
            user_with_orcid_id_verified,
            orcid_id_verified,
            eligible_institution,
            another_eligible_institution,
    ):
        mock_get_orcid_employment_sources.return_value = [
            eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.fullname,
        ]
        mock_get_orcid_education_sources.return_value = [
            another_eligible_institution.orcid_record_verified_source,
            user_with_orcid_id_verified.username,
        ]
        institution = tasks.check_institution_affiliation(orcid_id_verified)
        assert institution == eligible_institution

    @mock.patch('framework.auth.tasks.orcid_public_api_make_request')
    def test_get_orcid_employment_sources(
            self,
            mock_orcid_public_api_make_request,
            orcid_id_verified,
            eligible_institution,
            xml_data_employments,
    ):
        mock_orcid_public_api_make_request.return_value = xml_data_employments
        source_list = tasks.get_orcid_employment_sources(orcid_id_verified)
        assert len(source_list) == 2
        assert eligible_institution.orcid_record_verified_source in source_list
        assert 'An ORCiD User' in source_list

    @mock.patch('framework.auth.tasks.orcid_public_api_make_request')
    def test_get_orcid_education_sources(
            self,
            mock_orcid_public_api_make_request,
            orcid_id_verified,
            eligible_institution,
            xml_data_educations,
    ):
        mock_orcid_public_api_make_request.return_value = xml_data_educations
        source_list = tasks.get_orcid_education_sources(orcid_id_verified)
        assert len(source_list) == 2
        assert eligible_institution.orcid_record_verified_source in source_list
        assert 'An ORCiD User' in source_list

    @mock.patch('requests.get')
    def test_orcid_public_api_make_request_education_path(
            self,
            mock_get,
            orcid_id_verified,
            response_content_educations
    ):
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = response_content_educations
        mock_get.return_value = mock_response
        xml_data = tasks.orcid_public_api_make_request(ORCID_RECORD_EDUCATION_PATH, orcid_id_verified)
        assert xml_data is not None

    @mock.patch('requests.get')
    def test_orcid_public_api_make_request_employment_path(
            self,
            mock_get,
            orcid_id_verified,
            response_content_employments
    ):
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = response_content_employments
        mock_get.return_value = mock_response
        xml_data = tasks.orcid_public_api_make_request(ORCID_RECORD_EMPLOYMENT_PATH, orcid_id_verified)
        assert xml_data is not None

    # For failure cases, either education or employment path is sufficient.
    # Thus using the education path for the rest of the tests below to avoid duplicate tests

    @mock.patch('requests.get')
    @mock.patch('lxml.etree.XML')
    def test_orcid_public_api_make_request_not_200(
            self,
            mock_XML,
            mock_get,
            orcid_id_verified,
            response_content_educations
    ):
        mock_response = Response()
        mock_response.status_code = 204
        mock_response._content = None
        mock_get.return_value = mock_response
        xml_data = tasks.orcid_public_api_make_request(ORCID_RECORD_EDUCATION_PATH, orcid_id_verified)
        assert xml_data is None
        mock_XML.assert_not_called()

    @mock.patch('requests.get')
    def test_orcid_public_api_make_request_parsing_error(
            self,
            mock_get,
            orcid_id_verified,
            response_content_educations
    ):
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'invalid_xml'
        mock_get.return_value = mock_response
        xml_data = tasks.orcid_public_api_make_request(ORCID_RECORD_EDUCATION_PATH, orcid_id_verified)
        assert xml_data is None
