import pytest

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
