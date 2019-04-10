import pytest

from api.search.serializers import SearchSerializer
from api_tests import utils
from osf.models import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
)
from tests.utils import make_drf_request_with_version, mock_archive
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION


@pytest.mark.django_db
class TestSearchSerializer:

    def test_search_serializer_mixed_model(self):

        user = AuthUserFactory()
        project = ProjectFactory(creator=user, is_public=True)
        component = NodeFactory(parent=project, creator=user, is_public=True)
        file_component = utils.create_test_file(component, user)
        context = {'request': make_drf_request_with_version(version='2.0')}
        schema = RegistrationSchema.objects.filter(
            name='Replication Recipe (Brandt et al., 2013): Post-Completion',
            schema_version=LATEST_SCHEMA_VERSION).first()

        # test_search_serializer_mixed_model_project
        result = SearchSerializer(project, context=context).data
        assert result['data']['type'] == 'nodes'

        # test_search_serializer_mixed_model_component
        result = SearchSerializer(component, context=context).data
        assert result['data']['type'] == 'nodes'

        # test_search_serializer_mixed_model_registration
        with mock_archive(project, autocomplete=True, autoapprove=True, schema=schema) as registration:
            result = SearchSerializer(registration, context=context).data
            assert result['data']['type'] == 'registrations'

        # test_search_serializer_mixed_model_file
        result = SearchSerializer(file_component, context=context).data
        assert result['data']['type'] == 'files'

        # test_search_serializer_mixed_model_user
        result = SearchSerializer(user, context=context).data
        assert result['data']['type'] == 'users'
