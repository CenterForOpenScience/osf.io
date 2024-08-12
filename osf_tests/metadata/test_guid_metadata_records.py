import pytest
from django.core import exceptions as django_exceptions


from osf.models import GuidMetadataRecord
from osf_tests import factories
from api_tests.utils import create_test_file

GOOD_FUNDING_INFOS = (
    [],
    [
        {
            "funder_name": "hey",
            "funder_identifier": "look:",
            "funder_identifier_type": "ROR",
            "award_number": "string",
            "award_uri": "http://is.example",
            "award_title": "valid!",
        }
    ],
    [
        {
            "funder_name": "just the name is good enough",
        }
    ],
    [
        {
            "funder_name": "just",
        },
        {
            "funder_name": "the",
        },
        {
            "funder_name": "name",
        },
        {
            "funder_name": "is",
        },
        {
            "funder_name": "good",
        },
        {
            "funder_name": "enough",
        },
    ],
    [
        {
            "funder_name": "NIH probably",
            "funder_identifier": "https://doi.org/10.blah/deeblah",
            "funder_identifier_type": "Crossref Funder ID",
            "award_number": "27",
            "award_uri": "https://awards.example/twenty-seven",
            "award_title": "Award Twentyseven",
        },
        {
            "funder_name": "NSF probably",
            "funder_identifier": "https://doi.org/10.blah/dooblah",
            "funder_identifier_type": "Crossref Funder ID",
            "award_number": "28",
            "award_uri": "https://awards.example/twenty-eight",
            "award_title": "Award Twentyeight",
        },
        {
            "funder_name": "Mx. Moneypockets",
            "award_number": "10000000",
            "award_uri": "https://moneypockets.example/millions",
            "award_title": "Because i said so",
        },
    ],
)

BAD_FUNDING_INFOS = (
    [{}],
    [{"missing": "there is one required field"}],
    [{"funder_name": "ok", "unknown": "bad"}],
    [
        {
            "funder_name": "see award_number should be a string",
            "award_number": 7,
        }
    ],
    [
        {
            "funder_name": "this one is ok, but the empty object next in the array is not"
        },
        {},
    ],
    [
        {
            "funder_name": "bad funder_identifier_type",
            "funder_identifier_type": "something",
        }
    ],
    # TODO: consider installing the package that will make jsonschema validate format='uri'
    # [{'funder_name': 'bad award_uri', 'award_uri': 'not a uri'}],
)


@pytest.mark.django_db
class TestGuidMetadataRecord:
    @pytest.fixture
    def user(self):
        return factories.UserFactory()

    @pytest.fixture
    def project(self, user):
        return factories.ProjectFactory(creator=user)

    @pytest.fixture
    def registration(self, project):
        return factories.RegistrationFactory(project=project)

    @pytest.fixture
    def file(self, project, user):
        return create_test_file(project, user)

    @pytest.mark.enable_implicit_clean
    def test_funding_validation(self, project, registration, file):
        for referent in (project, registration, file):
            metadata_record = GuidMetadataRecord.objects.for_guid(project._id)
            for bad_funding_info in BAD_FUNDING_INFOS:
                metadata_record.funding_info = bad_funding_info
                with pytest.raises(django_exceptions.ValidationError):
                    metadata_record.save()

            for good_funding_info in GOOD_FUNDING_INFOS:
                metadata_record.funding_info = good_funding_info
                metadata_record.save()  # note the absence of ValidationError
                metadata_record.refresh_from_db()
                assert metadata_record.funding_info == good_funding_info
