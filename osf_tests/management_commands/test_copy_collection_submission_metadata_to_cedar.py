import pytest
from faker import Faker
from unittest import mock

from django.core.management import call_command

from osf.management.commands.copy_collection_submission_metadata_to_cedar import (
    copy_collection_submission_metadata_to_cedar,
)
from osf.models import CollectionSubmission, CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import (
    CollectionFactory,
    CollectionProviderFactory,
    NodeFactory,
)
from tests.utils import capture_notifications

fake = Faker()


def _value_property():
    return {'type': 'object', 'properties': {'@value': {'type': 'string'}}}


CEDAR_SCHEMA = {
    'type': 'object',
    'properties': {
        '@context': {'type': 'object'},
        'Collected Type': _value_property(),
        'Status': _value_property(),
        'Volume': _value_property(),
        'Issue': _value_property(),
        'Program Area': _value_property(),
        'School Type': _value_property(),
        'Study Design': _value_property(),
        'Data Type': _value_property(),
        'Disease': _value_property(),
        'Grade Levels': _value_property(),
    },
    'required': ['@id', 'pav:createdOn', 'pav:createdBy', 'pav:lastUpdatedOn', 'oslc:modifiedBy'],
    'additionalProperties': True,
}

CEDAR_SCHEMA_WITH_REQUIRED_FIELD = {
    **CEDAR_SCHEMA,
    'required': CEDAR_SCHEMA['required'] + ['School Type'],
}


def make_cedar_template(template=CEDAR_SCHEMA):
    return CedarMetadataTemplate.objects.create(
        schema_name=fake.bs(),
        cedar_id=fake.md5(),
        template_version=1,
        template=template,
        active=True,
    )


def make_collection(provider):
    collection = CollectionFactory()
    collection.provider = provider
    collection.save()
    return collection


def make_submission(collection, **fields):
    node = NodeFactory(is_public=True)
    submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=collection,
        creator=node.creator,
        **fields,
    )
    with capture_notifications():
        submission.save()
    return submission


@pytest.fixture()
def cedar_template():
    return make_cedar_template()


@pytest.fixture()
def provider_with_template(cedar_template):
    provider = CollectionProviderFactory()
    provider.required_metadata_template = cedar_template
    provider.save()
    return provider


@pytest.fixture()
def provider_without_template():
    return CollectionProviderFactory()


@pytest.mark.django_db
class TestCopyCollectionSubmissionMetadataToCedar:

    def test_creates_record_for_submission_with_template(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, collected_type='software', status='active')

        copy_collection_submission_metadata_to_cedar()

        assert CedarMetadataRecord.objects.filter(
            guid=submission.guid,
            template=cedar_template,
        ).exists()

    def test_record_contains_non_empty_fields_only(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, collected_type='dataset', status='', volume='')

        copy_collection_submission_metadata_to_cedar()

        record = CedarMetadataRecord.objects.get(guid=submission.guid, template=cedar_template)
        assert record.metadata == {'Collected Type': {'@value': 'dataset'}}

    def test_record_is_published(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, status='active')

        copy_collection_submission_metadata_to_cedar()

        record = CedarMetadataRecord.objects.get(guid=submission.guid, template=cedar_template)
        assert record.is_published is True

    def test_updates_existing_record(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, status='new')
        CedarMetadataRecord.objects.create(
            guid=submission.guid,
            template=cedar_template,
            metadata={'status': 'old'},
            is_published=False,
        )

        copy_collection_submission_metadata_to_cedar()

        record = CedarMetadataRecord.objects.get(guid=submission.guid, template=cedar_template)
        assert record.metadata == {'Status': {'@value': 'new'}}
        assert record.is_published is True

    def test_skips_submissions_without_required_template(self, provider_without_template):
        collection = make_collection(provider_without_template)
        submission = make_submission(collection, collected_type='software')

        copy_collection_submission_metadata_to_cedar()

        assert not CedarMetadataRecord.objects.filter(guid=submission.guid).exists()

    def test_dry_run_makes_no_changes(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, collected_type='software')

        copy_collection_submission_metadata_to_cedar(dry_run=True)

        assert not CedarMetadataRecord.objects.filter(guid=submission.guid).exists()

    def test_provider_filter_processes_only_matching_provider(self, cedar_template):
        provider_a = CollectionProviderFactory()
        provider_a.required_metadata_template = cedar_template
        provider_a.save()

        provider_b = CollectionProviderFactory()
        provider_b.required_metadata_template = make_cedar_template()
        provider_b.save()

        sub_a = make_submission(make_collection(provider_a), collected_type='software')
        sub_b = make_submission(make_collection(provider_b), collected_type='dataset')

        copy_collection_submission_metadata_to_cedar(provider_id=provider_a._id)

        assert CedarMetadataRecord.objects.filter(guid=sub_a.guid, template=cedar_template).exists()
        assert not CedarMetadataRecord.objects.filter(guid=sub_b.guid).exists()

    def test_error_on_one_does_not_stop_others(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        make_submission(collection, collected_type='software')
        make_submission(collection, collected_type='dataset')

        with mock.patch.object(CollectionSubmission, 'sync_cedar_metadata') as mock_sync:
            mock_sync.side_effect = [Exception('simulated error'), None]
            copy_collection_submission_metadata_to_cedar()

        assert mock_sync.call_count == 2

    def test_call_command_interface(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, collected_type='software')

        call_command('copy_collection_submission_metadata_to_cedar')

        assert CedarMetadataRecord.objects.filter(
            guid=submission.guid,
            template=cedar_template,
        ).exists()

    def test_call_command_dry_run(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, collected_type='software')

        call_command('copy_collection_submission_metadata_to_cedar', dry_run=True)

        assert not CedarMetadataRecord.objects.filter(guid=submission.guid).exists()

    def test_all_cedar_fields_copied(self, provider_with_template, cedar_template):
        collection = make_collection(provider_with_template)
        submission = make_submission(
            collection,
            collected_type='software',
            status='active',
            volume='1',
            issue='2',
            program_area='health',
            school_type='university',
            study_design='rct',
            data_type='quantitative',
            disease='cancer',
            grade_levels='K-12',
        )

        copy_collection_submission_metadata_to_cedar()

        record = CedarMetadataRecord.objects.get(guid=submission.guid, template=cedar_template)
        assert record.metadata == {
            'Collected Type': {'@value': 'software'},
            'Status': {'@value': 'active'},
            'Volume': {'@value': '1'},
            'Issue': {'@value': '2'},
            'Program Area': {'@value': 'health'},
            'School Type': {'@value': 'university'},
            'Study Design': {'@value': 'rct'},
            'Data Type': {'@value': 'quantitative'},
            'Disease': {'@value': 'cancer'},
            'Grade Levels': {'@value': 'K-12'},
        }

    def test_satisfies_template_required_field(self, provider_with_template, cedar_template):
        cedar_template.template = CEDAR_SCHEMA_WITH_REQUIRED_FIELD
        cedar_template.save()
        collection = make_collection(provider_with_template)
        submission = make_submission(collection, school_type='university')

        copy_collection_submission_metadata_to_cedar()

        record = CedarMetadataRecord.objects.get(guid=submission.guid, template=cedar_template)
        assert record.is_published is True
        assert record.metadata == {'School Type': {'@value': 'university'}}
