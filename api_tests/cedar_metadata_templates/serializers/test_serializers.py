import pytest
from urllib.parse import urlparse

from api.base.settings.defaults import API_PRIVATE_BASE
from api.cedar_metadata_templates.serializers import CedarMetadataTemplateSerializer

from osf.models import CedarMetadataTemplate

from tests.utils import make_drf_request_with_version


@pytest.fixture()
def cedar_template_json():
    return {'t_key_1': 't_value_1', 't_key_2': 't_value_2', 't_key_3': 't_value_3'}

@pytest.fixture()
def cedar_template(cedar_template_json):
    return CedarMetadataTemplate.objects.create(
        schema_name='cedar_test_schema_name',
        cedar_id='cedar_test_id',
        template_version=1,
        template=cedar_template_json,
        active=True,
    )


@pytest.mark.django_db
class TestCedarMetadataTemplateSerializer:

    def test_serializer(self, cedar_template):

        context = {'request': make_drf_request_with_version()}
        data = CedarMetadataTemplateSerializer(cedar_template, context=context).data['data']
        assert data['id'] == cedar_template._id
        assert data['type'] == 'cedar-metadata-templates'

        # Attributes
        assert data['attributes']['schema_name'] == cedar_template.schema_name
        assert data['attributes']['cedar_id'] == cedar_template.cedar_id
        assert data['attributes']['template'] == cedar_template.template
        assert data['attributes']['active'] is True
        assert data['attributes']['template_version'] == cedar_template.template_version

        # Links
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/'
