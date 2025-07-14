import pytest
from unittest import mock

from django.core.management import call_command
from osf_tests.factories import PreprintFactory, PreprintProviderFactory


@pytest.mark.django_db
class TestFixPreprintsHasDataLinksAndWhyNoData:

    @pytest.fixture()
    def preprint_not_no_with_why_no_data(self):
        preprint = PreprintFactory()
        preprint.has_data_links = 'available'
        preprint.why_no_data = 'This should be cleared'
        preprint.save()
        return preprint

    @pytest.fixture()
    def preprint_no_with_why_no_data(self):
        preprint = PreprintFactory()
        preprint.has_data_links = 'no'
        preprint.why_no_data = 'Valid reason'
        preprint.save()
        return preprint

    @pytest.fixture()
    def preprint_not_applicable_with_why_no_data(self):
        preprint = PreprintFactory()
        preprint.has_data_links = 'not_applicable'
        preprint.why_no_data = 'This should be cleared'
        preprint.save()
        return preprint

    def test_fix_preprints_has_data_links_and_why_no_data(
        self, preprint_not_no_with_why_no_data, preprint_no_with_why_no_data, preprint_not_applicable_with_why_no_data
    ):
        call_command('fix_preprints_has_data_links_and_why_no_data')

        preprint_not_no_with_why_no_data.refresh_from_db()
        preprint_no_with_why_no_data.refresh_from_db()
        preprint_not_applicable_with_why_no_data.refresh_from_db()

        assert preprint_not_no_with_why_no_data.why_no_data == ''
        assert preprint_not_applicable_with_why_no_data.why_no_data == ''

        assert preprint_no_with_why_no_data.why_no_data == 'Valid reason'

    def test_dry_run_mode(self, preprint_not_no_with_why_no_data):
        call_command('fix_preprints_has_data_links_and_why_no_data', '--dry-run')

        preprint_not_no_with_why_no_data.refresh_from_db()
        assert preprint_not_no_with_why_no_data.why_no_data == 'This should be cleared'

    def test_specific_guid(self):

        preprint1 = PreprintFactory()
        preprint1.has_data_links = 'available'
        preprint1.why_no_data = 'This should be cleared'
        preprint1.save()

        preprint2 = PreprintFactory()
        preprint2.has_data_links = 'available'
        preprint2.why_no_data = 'This should remain'
        preprint2.save()

        call_command('fix_preprints_has_data_links_and_why_no_data', '--guid', f'{preprint1._id}')

        preprint1.refresh_from_db()
        preprint2.refresh_from_db()

        assert preprint1.why_no_data == ''
        assert preprint2.why_no_data == 'This should remain'

    def test_no_action_for_correct_preprints(self):
        preprint = PreprintFactory()
        preprint.has_data_links = 'available'
        preprint.why_no_data = ''
        preprint.save()

        with mock.patch('osf.models.Guid.split_guid', return_value=(preprint._id, 1)):
            call_command('fix_preprints_has_data_links_and_why_no_data', '--guid', f'{preprint._id}_v1')

        preprint.refresh_from_db()

        assert preprint.has_data_links == 'available'
        assert preprint.why_no_data == ''

    def test_preprints_with_null_has_data_links(self):
        preprint = PreprintFactory()
        preprint.has_data_links = None
        preprint.why_no_data = 'Should be cleared for null has_data_links'
        preprint.save()

        call_command('fix_preprints_has_data_links_and_why_no_data')

        preprint.refresh_from_db()
        assert preprint.why_no_data == ''

    def test_preprints_different_providers(self):
        provider1 = PreprintProviderFactory()
        provider2 = PreprintProviderFactory()

        preprint1 = PreprintFactory(provider=provider1)
        preprint1.has_data_links = 'available'
        preprint1.why_no_data = 'Should be cleared (provider 1)'
        preprint1.save()

        preprint2 = PreprintFactory(provider=provider2)
        preprint2.has_data_links = 'not_applicable'
        preprint2.why_no_data = 'Should be cleared (provider 2)'
        preprint2.save()

        call_command('fix_preprints_has_data_links_and_why_no_data')

        preprint1.refresh_from_db()
        preprint2.refresh_from_db()

        assert preprint1.why_no_data == ''
        assert preprint2.why_no_data == ''

    def test_preprints_with_data_links(self):
        preprint = PreprintFactory()
        preprint.has_data_links = 'available'
        preprint.data_links = ['https://example.com/dataset123']
        preprint.why_no_data = 'This contradicts having data links'
        preprint.save()

        call_command('fix_preprints_has_data_links_and_why_no_data')

        preprint.refresh_from_db()
        assert preprint.why_no_data == ''
        assert preprint.data_links == ['https://example.com/dataset123']

    def test_error_handling(self):
        preprint1 = PreprintFactory()
        preprint1.has_data_links = 'available'
        preprint1.why_no_data = 'Should be cleared'
        preprint1.save()

        preprint2 = PreprintFactory()
        preprint2.has_data_links = 'available'
        preprint2.why_no_data = 'Should be cleared too'
        preprint2.save()

        preprint3 = PreprintFactory()
        preprint3.has_data_links = 'available'
        preprint3.why_no_data = 'Should also be cleared'
        preprint3.save()

        call_command('fix_preprints_has_data_links_and_why_no_data')

        preprint1.refresh_from_db()
        preprint3.refresh_from_db()

        assert preprint1.why_no_data == ''
        assert preprint3.why_no_data == ''
