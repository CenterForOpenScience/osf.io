import mock
import pytest

from osf_tests.factories import PreprintFactory
from osf.models import Identifier, PreprintService
from scripts.add_identifiers_to_existing_preprints import add_identifiers_to_preprints

pytestmark = pytest.mark.django_db


class TestAddIdentifiersToPreprints:

    def test_preprints_get_identifiers(self):

        # Create some preprints
        PreprintFactory()
        PreprintFactory()

        # Remove all Identifiers
        Identifier.objects.all().delete()

        assert PreprintService.objects.all().exists()
        assert not Identifier.objects.all().exists()

        create_identifier_patcher = mock.patch("website.identifiers.client.EzidClient.create_identifier")
        mock_create_identifier = create_identifier_patcher.start()
        mock_create_identifier.return_value = {'success': 'doi:test_doi | ark:test_ark'}

        # run the main function of the script
        add_identifiers_to_preprints()
        create_identifier_patcher.stop()

        assert Identifier.objects.all().exists()
        assert PreprintService.objects.all().exists()

        for preprint in PreprintService.objects.all():
            assert preprint.get_identifier('doi')
            assert preprint.get_identifier('ark')
