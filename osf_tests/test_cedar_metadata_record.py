import pytest
from faker import Faker
from django.core.exceptions import ValidationError

from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import AuthUserFactory, ProjectFactory

fake = Faker()

CEDAR_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'type': 'object',
    'properties': {
        '@context': {'type': 'object'},
        'School Type': {
            'type': 'object',
            'properties': {'@value': {'type': 'string'}},
        },
    },
    'required': ['@id', 'pav:createdOn', 'pav:createdBy', 'pav:lastUpdatedOn', 'oslc:modifiedBy', 'School Type'],
    'additionalProperties': True,
}


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def node(user):
    return ProjectFactory(creator=user)


@pytest.fixture()
def cedar_template():
    return CedarMetadataTemplate.objects.create(
        schema_name=fake.bs(),
        cedar_id=fake.md5(),
        template_version=1,
        template=CEDAR_SCHEMA,
        active=True,
    )


@pytest.mark.django_db
class TestCedarMetadataRecordClean:

    def _make_record(self, node, cedar_template, metadata, is_published=True):
        record = CedarMetadataRecord(
            guid=node.guids.first(),
            template=cedar_template,
            metadata=metadata,
            is_published=is_published,
        )
        return record

    def test_provenance_fields_stripped_from_required(self, node, cedar_template):
        record = self._make_record(node, cedar_template, {
            'School Type': {'@value': 'High School'},
        })
        record.clean()

    def test_empty_dict_properties_stripped_from_metadata(self, node, cedar_template):
        record = self._make_record(node, cedar_template, {
            'School Type': {'@value': 'High School'},
            '3de6ff2c-555b-44d4-84b6-3862188d29c9': {},
        })
        record.clean()

    def test_invalid_metadata_raises_validation_error(self, node, cedar_template):
        record = self._make_record(node, cedar_template, {
            'School Type': 'not-an-object',
        })
        with pytest.raises(ValidationError, match='does not validate against template'):
            record.clean()

    def test_missing_non_provenance_required_field_raises(self, node, cedar_template):
        record = self._make_record(node, cedar_template, {})
        with pytest.raises(ValidationError, match='does not validate against template'):
            record.clean()

    def test_draft_record_skips_validation(self, node, cedar_template):
        record = self._make_record(node, cedar_template, {}, is_published=False)
        record.clean()

    def test_template_required_list_not_mutated(self, node, cedar_template):
        original_required = list(cedar_template.template['required'])
        record = self._make_record(node, cedar_template, {
            'School Type': {'@value': 'High School'},
        })
        record.clean()
        assert cedar_template.template['required'] == original_required
