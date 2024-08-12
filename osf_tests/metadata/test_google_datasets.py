from tests.base import OsfTestCase
from osf_tests import factories
from osf.metadata.tools import pls_gather_metadata_as_dict
from osf.metadata.serializers import GoogleDatasetJsonLdSerializer


class TestGoogleDatasetJsonLdSerializer(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.project_description_short = factories.ProjectFactory(
            description="Under 50"
        )
        self.project_description_null = factories.ProjectFactory(
            description=""
        )
        self.project_description_50_chars = factories.ProjectFactory(
            description="N" * 50
        )

    def test_description_short(self):
        result_metadata = pls_gather_metadata_as_dict(
            self.project_description_short, "google-dataset-json-ld"
        )
        assert (
            result_metadata["description"]
            == GoogleDatasetJsonLdSerializer.DEFAULT_DESCRIPTION
        )

    def test_description_null(self):
        result_metadata = pls_gather_metadata_as_dict(
            self.project_description_null, "google-dataset-json-ld"
        )
        assert (
            result_metadata["description"]
            == GoogleDatasetJsonLdSerializer.DEFAULT_DESCRIPTION
        )

    def test_description_50(self):
        result_metadata = pls_gather_metadata_as_dict(
            self.project_description_50_chars, "google-dataset-json-ld"
        )
        assert (
            result_metadata["description"]
            == self.project_description_50_chars.description
        )
