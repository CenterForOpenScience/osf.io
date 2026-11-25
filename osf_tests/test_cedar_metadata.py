import pytest
from django.core.exceptions import ValidationError

from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import AuthUserFactory, ProjectFactory


@pytest.mark.django_db
class TestCedarMetadataRecordClean:

    def test_clean_filters_context_items_not_in_schema_required(self):
        template = CedarMetadataTemplate.objects.create(
            schema_name='cedar_test_schema',
            cedar_id='cedar_test_id',
            template_version=1,
            template={
                'type': 'object',
                'properties': {
                    '@context': {
                        'type': 'object',
                        'required': ['foo', 'bar'],
                        'properties': {
                            'foo': {'type': 'string'},
                            'bar': {'type': 'string'},
                        },
                        'additionalProperties': False,
                    },
                },
                'required': ['@context'],
            },
            active=True,
        )
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        record = CedarMetadataRecord(
            guid=project.guids.first(),
            template=template,
            metadata={'@context': {'foo': 'value1', 'bar': 'value2', 'extra': 'drop'}},
            is_published=True,
        )

        record.clean()  # should not raise after filtering @context items
        assert record.metadata == {'@context': {'foo': 'value1', 'bar': 'value2'}}

    @staticmethod
    def _element(context_properties, additional_context=False):
        return {
            'type': 'object',
            'properties': {
                '@context': {
                    'type': 'object',
                    'properties': {key: {'type': 'string'} for key in context_properties},
                    'additionalProperties': additional_context,
                },
                **{key: {'type': 'object'} for key in context_properties},
            },
        }

    def _make_record(self, template, metadata):
        return CedarMetadataRecord(
            guid=ProjectFactory(creator=AuthUserFactory()).guids.first(),
            template=CedarMetadataTemplate.objects.create(
                schema_name='cedar_test_schema',
                cedar_id='cedar_test_id',
                template_version=1,
                template=template,
                active=True,
            ),
            metadata=metadata,
            is_published=True,
        )

    def test_clean_filters_nested_context_items_not_in_schema(self):
        template = self._element(['Dataset', 'Creator'])
        template['properties']['Dataset'] = self._element(['Modality'])
        template['properties']['Creator'] = {'type': 'array', 'items': self._element(['Name'])}
        record = self._make_record(template, {
            '@context': {'Dataset': 'iri', 'Creator': 'iri', 'About': 'static'},
            'Dataset': {
                '@context': {'Modality': 'iri', 'Modality instruction': 'static'},
                'Modality': {'@value': 'Behavior'},
            },
            'Creator': [
                {'@context': {'Name': 'iri', 'Name instruction': 'static'}, 'Name': {'@value': 'one'}},
                {'@context': {'Name': 'iri', 'Name instruction': 'static'}, 'Name': {'@value': 'two'}},
            ],
        })

        record.clean()
        assert record.metadata == {
            '@context': {'Dataset': 'iri', 'Creator': 'iri'},
            'Dataset': {'@context': {'Modality': 'iri'}, 'Modality': {'@value': 'Behavior'}},
            'Creator': [
                {'@context': {'Name': 'iri'}, 'Name': {'@value': 'one'}},
                {'@context': {'Name': 'iri'}, 'Name': {'@value': 'two'}},
            ],
        }

    def test_clean_keeps_extra_context_items_where_schema_allows_them(self):
        template = self._element(['Paradigm'])
        template['properties']['Paradigm'] = self._element(['Stimulus'], additional_context={'type': 'string'})
        record = self._make_record(template, {
            '@context': {'Paradigm': 'iri'},
            'Paradigm': {
                '@context': {'Stimulus': 'iri', 'custom attribute': 'attribute-iri'},
                'Stimulus': {'@value': 'Visual'},
            },
        })

        record.clean()
        assert record.metadata['Paradigm']['@context'] == {'Stimulus': 'iri', 'custom attribute': 'attribute-iri'}

    @staticmethod
    def _multiple_choice(required):
        return {
            'type': 'array',
            'minItems': 1,
            'items': {
                'type': 'object',
                '_valueConstraints': {'requiredValue': required, 'multipleChoice': True},
            },
        }

    def test_clean_allows_empty_optional_multiple_choice(self):
        template = self._element(['Standard', 'Status'])
        template['properties']['Standard'] = self._multiple_choice(required=False)
        template['properties']['Status'] = self._multiple_choice(required=True)
        record = self._make_record(template, {
            '@context': {'Standard': 'iri', 'Status': 'iri'},
            'Standard': [],
            'Status': [{'@value': 'Preprocessed'}],
        })

        record.clean()
        assert record.template.template['properties']['Standard']['minItems'] == 1

    def test_clean_requires_required_multiple_choice(self):
        template = self._element(['Status'])
        template['properties']['Status'] = self._multiple_choice(required=True)
        record = self._make_record(template, {'@context': {'Status': 'iri'}, 'Status': []})

        with pytest.raises(ValidationError, match='should be non-empty'):
            record.clean()
