from unittest import mock
from urllib.parse import urljoin

import pytest
import responses

from osf.exceptions import (
    InvalidPIDError,
    InvalidPIDFormatError,
    NoSuchPIDError,
)
from osf.models import Identifier
from osf.utils.identifiers import PID_VALIDATION_ENDPOINTS
from osf_tests.factories import RegistrationFactory


DOI_VALIDATION_ENDPOINT = PID_VALIDATION_ENDPOINTS["doi"]

VALID_RESPONSE = '[{"RA": "DataCite"}]'
INVALID_DOI_RESPONSE = '[{"status": "Invalid DOI"}]'
NO_SUCH_DOI_RESPONSE = '[{"status": "DOI does not exist"}]'
UNRECOGNIZED_DOI_RESPONSE = '[{"status": "Here there be monsters"}]'


@pytest.mark.django_db
@mock.patch("osf.utils.identifiers.PID_VALIDATION_ENABLED", True)
class TestIdentifier:
    @pytest.fixture
    def external_identifier(self):
        return Identifier.objects.create(
            referent=None, value="DOI", category="doi"
        )

    @pytest.fixture
    def internal_identifier(self):
        registration = RegistrationFactory(has_doi=True)
        return registration.get_identifier("doi")

    @responses.activate
    def test_validate__valid_value(self, external_identifier):
        responses.add(
            method=responses.GET,
            url=urljoin(DOI_VALIDATION_ENDPOINT, external_identifier.value),
            body=VALID_RESPONSE,
            status=200,
            content_type="application/json",
        )

        assert external_identifier.validate_identifier_value()
        assert responses.calls

    @pytest.mark.parametrize(
        "response_body, expected_error",
        [
            (INVALID_DOI_RESPONSE, InvalidPIDFormatError),
            (NO_SUCH_DOI_RESPONSE, NoSuchPIDError),
            (UNRECOGNIZED_DOI_RESPONSE, InvalidPIDError),
        ],
    )
    @responses.activate
    def test_validate__invalid_value_reraises(
        self, response_body, expected_error, external_identifier
    ):
        responses.add(
            method=responses.GET,
            url=urljoin(DOI_VALIDATION_ENDPOINT, external_identifier.value),
            body=response_body,
            status=200,
            content_type="application/json",
        )

        with pytest.raises(expected_error):
            external_identifier.validate_identifier_value()

        assert responses.calls

    @responses.activate
    def test_validate__internal_identifier_bypasses_validation(
        self, internal_identifier
    ):
        with responses.RequestsMock(
            assert_all_requests_are_fired=False
        ) as rsps:
            rsps.add(
                responses.GET,
                urljoin(DOI_VALIDATION_ENDPOINT, internal_identifier.value),
                body=INVALID_DOI_RESPONSE,
                status=200,
                content_type="application/json",
            )
            assert internal_identifier.validate_identifier_value()

        # The validation endpoint should not have been hit
        assert not rsps.calls

    def test_validate__unsupported_pid_type_returns_true(
        self, external_identifier
    ):
        external_identifier.category = "arbitrary"
        external_identifier.save()

        assert external_identifier.validate_identifier_value()
