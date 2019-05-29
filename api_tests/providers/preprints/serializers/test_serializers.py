import pytest
from django.utils import timezone

from api.preprint_providers.serializers import DeprecatedPreprintProviderSerializer
from api.preprints.serializers import PreprintSerializer
from osf_tests.factories import (
    PreprintProviderFactory,
    PreprintFactory,
)
from tests.utils import make_drf_request_with_version

@pytest.fixture()
def preprint():
    return PreprintFactory()

@pytest.mark.django_db
class TestRetractedPreprintSerialization:

    def test_hidden_fields_on_retracted_preprint(self, preprint):
        hide_if_withdrawal_fields = {
            'is_published', 'is_preprint_orphan', 'license_record',
            'preprint_doi_created'
        }
        hide_if_not_withdrawal_fields = {'withdrawal_justification'}
        always_show_fields = {
            'date_created', 'date_modified', 'date_published', 'original_publication_date',
            'doi', 'title', 'description', 'date_withdrawn', 'tags'}

        # test_non_retracted
        req = make_drf_request_with_version()
        result = PreprintSerializer(
            preprint,
            context={'request': req}).data
        data = result['data']
        attributes = set(data['attributes'])

        assert not preprint.is_retracted
        assert hide_if_not_withdrawal_fields.isdisjoint(attributes)
        assert always_show_fields.issubset(attributes)
        assert hide_if_withdrawal_fields.issubset(attributes)

        # test_retracted
        preprint.date_withdrawn = timezone.now()
        preprint.save()
        preprint.reload()

        result = PreprintSerializer(
            preprint,
            context={'request': req}).data
        data = result['data']
        attributes = set(data['attributes'])

        assert preprint.is_retracted
        assert always_show_fields.issubset(attributes)
        assert hide_if_not_withdrawal_fields.issubset(attributes)
        assert all(list([data['attributes'][field] is None for field in list(hide_if_withdrawal_fields)]))


@pytest.mark.django_db
class TestDeprecatedPreprintProviderSerializer:

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    def test_preprint_provider_serialization_versions(self, preprint_provider):
        # test_preprint_provider_serialization_v2
        req = make_drf_request_with_version(version='2.0')
        result = DeprecatedPreprintProviderSerializer(
            preprint_provider,
            context={'request': req}
        ).data

        data = result['data']
        attributes = data['attributes']

        assert data['id'] == preprint_provider._id
        assert data['type'] == 'preprint_providers'

        assert 'banner_path' in attributes
        assert 'logo_path' in attributes
        assert 'header_text' in attributes
        assert 'email_contact' in attributes
        assert 'email_support' in attributes
        assert 'social_facebook' in attributes
        assert 'social_instagram' in attributes
        assert 'social_twitter' in attributes
        assert 'subjects_acceptable' in attributes

        # test_preprint_provider_serialization_v24
        req = make_drf_request_with_version(version='2.4')
        result = DeprecatedPreprintProviderSerializer(
            preprint_provider,
            context={'request': req}
        ).data

        data = result['data']
        attributes = data['attributes']

        assert data['id'] == preprint_provider._id
        assert data['type'] == 'preprint_providers'

        assert 'banner_path' not in attributes
        assert 'logo_path' not in attributes
        assert 'header_text' not in attributes
        assert 'email_contact' not in attributes
        assert 'social_facebook' not in attributes
        assert 'social_instagram' not in attributes
        assert 'social_twitter' not in attributes

        # # test_preprint_provider_serialization_v25
        req = make_drf_request_with_version(version='2.5')
        result = DeprecatedPreprintProviderSerializer(
            preprint_provider,
            context={'request': req}
        ).data

        data = result['data']
        attributes = data['attributes']

        assert data['id'] == preprint_provider._id
        assert data['type'] == 'preprint_providers'

        assert 'banner_path' not in attributes
        assert 'logo_path' not in attributes
        assert 'header_text' not in attributes
        assert 'email_contact' not in attributes
        assert 'social_facebook' not in attributes
        assert 'social_instagram' not in attributes
        assert 'social_twitter' not in attributes
        assert 'subjects_acceptable' not in attributes

        assert 'name' in attributes
        assert 'description' in attributes
        assert 'advisory_board' in attributes
        assert 'example' in attributes
        assert 'domain' in attributes
        assert 'domain_redirect_enabled' in attributes
        assert 'footer_links' in attributes
        assert 'share_source' in attributes
        assert 'share_publish_type' in attributes
        assert 'email_support' in attributes
        assert 'preprint_word' in attributes
        assert 'allow_submissions' in attributes
        assert 'additional_providers' in attributes
