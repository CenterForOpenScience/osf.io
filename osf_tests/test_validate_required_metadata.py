import pytest
from faker import Faker
from django.core.exceptions import ValidationError

from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import AuthUserFactory, PreprintFactory, PreprintProviderFactory

fake = Faker()

VALID_JSONSCHEMA = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'type': 'object',
    'properties': {
        'title': {'type': 'string'},
    },
    'required': ['title'],
}


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def provider():
    return PreprintProviderFactory()


@pytest.fixture()
def cedar_template():
    return CedarMetadataTemplate.objects.create(
        schema_name=fake.bs(),
        cedar_id=fake.md5(),
        template_version=1,
        template=VALID_JSONSCHEMA,
        active=True,
    )


@pytest.fixture()
def preprint(user, provider):
    return PreprintFactory(creator=user, provider=provider)


@pytest.mark.django_db
class TestValidateRequiredMetadata:

    def test_no_required_template_passes(self, provider, preprint):
        assert provider.required_metadata_template is None
        provider.validate_required_metadata(preprint)

    def test_missing_record_raises(self, provider, cedar_template, preprint):
        provider.required_metadata_template = cedar_template
        provider.save()

        with pytest.raises(ValidationError, match='published CEDAR metadata record'):
            provider.validate_required_metadata(preprint)

    def test_unpublished_record_raises(self, provider, cedar_template, preprint):
        provider.required_metadata_template = cedar_template
        provider.save()

        CedarMetadataRecord.objects.create(
            guid=preprint.guids.first(),
            template=cedar_template,
            metadata={'title': 'My Preprint'},
            is_published=False,
        )

        with pytest.raises(ValidationError, match='published CEDAR metadata record'):
            provider.validate_required_metadata(preprint)

    def test_published_valid_record_passes(self, provider, cedar_template, preprint):
        provider.required_metadata_template = cedar_template
        provider.save()

        CedarMetadataRecord.objects.create(
            guid=preprint.guids.first(),
            template=cedar_template,
            metadata={'title': 'My Preprint'},
            is_published=True,
        )

        provider.validate_required_metadata(preprint)

    def test_published_invalid_record_raises(self, provider, cedar_template, preprint):
        provider.required_metadata_template = cedar_template
        provider.save()

        CedarMetadataRecord.objects.create(
            guid=preprint.guids.first(),
            template=cedar_template,
            metadata={'title': 123},
            is_published=True,
        )

        with pytest.raises(ValidationError):
            provider.validate_required_metadata(preprint)

    def test_record_for_wrong_template_raises(self, provider, cedar_template, preprint):
        provider.required_metadata_template = cedar_template
        provider.save()

        other_template = CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template=VALID_JSONSCHEMA,
            active=True,
        )
        CedarMetadataRecord.objects.create(
            guid=preprint.guids.first(),
            template=other_template,
            metadata={'title': 'My Preprint'},
            is_published=True,
        )

        with pytest.raises(ValidationError, match='published CEDAR metadata record'):
            provider.validate_required_metadata(preprint)
