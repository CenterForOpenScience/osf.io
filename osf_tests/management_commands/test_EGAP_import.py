# encoding: utf-8
import os
import pytest
import responses
HERE = os.path.dirname(os.path.abspath(__file__))

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ApiOAuth2PersonalTokenFactory
)
from osf.models import (
    RegistrationSchema,
    ApiOAuth2PersonalToken
)

from osf.management.commands.import_EGAP import (
    ensure_egap_schema,
    create_node_from_project_json,
    recursive_upload,
    get_creator_auth_header
)

from website.settings import WATERBUTLER_INTERNAL_URL


@pytest.mark.django_db
class TestEGAPImport:

    @pytest.fixture()
    def greg(self):
        return AuthUserFactory(username='greg@greg.com')

    @pytest.fixture()
    def node(self, greg):
        return NodeFactory(creator=greg)

    @pytest.fixture()
    def egap_assets_path(self):
        return os.path.join(HERE, 'test_directory', 'EGAP')

    @pytest.fixture()
    def egap_project_name(self):
        return '20120220AA'

    def test_get_creator_auth_header(self, greg):
        greg, auth_header = get_creator_auth_header(greg.username)

        gregs_token = ApiOAuth2PersonalToken.objects.get(owner=greg).token_id
        assert auth_header['Authorization'] == 'Bearer {}'.format(gregs_token)

    def test_ensure_egap_schema(self):
        ensure_egap_schema()

        assert RegistrationSchema.objects.get(name='EGAP Registration')

    def test_create_node_from_project_json(self, egap_assets_path, egap_project_name, greg):
        node = create_node_from_project_json(egap_assets_path, egap_project_name, greg)

        assert node.title == 'Home Security and Infidelity: a case study by Fletcher Cox'
        assert node.creator == greg

        assert len(node.contributors.all()) == 5
        assert node.contributors.exclude(username='greg@greg.com').first().fullname == 'Fletcher Cox'
        assert not node.get_visible(greg)

    @responses.activate
    def test_recursive_and_upload(self, node, greg, egap_assets_path, egap_project_name):
        responses.add(
            responses.Response(
                responses.PUT,
                '{}/v1/resources/{}/providers/osfstorage/?name=test_folder&kind=folder'.format(
                    WATERBUTLER_INTERNAL_URL,
                    node._id,
                ),
                json={'data': {'attributes': {'path': 'parent'}}},
                status=201,
            )
        )
        responses.add(
            responses.Response(
                responses.PUT,
                '{}/v1/resources/{}/providers/osfstorage/parent?name=test-2.txt&kind=file'.format(
                    WATERBUTLER_INTERNAL_URL,
                    node._id,
                ),
                json={'metadata': 'for test-2!'},
                status=201,
            )
        )
        responses.add(
            responses.Response(
                responses.PUT,
                '{}/v1/resources/{}/providers/osfstorage/?name=test-1.txt&kind=file'.format(
                    WATERBUTLER_INTERNAL_URL,
                    node._id,
                ),
                json={'metadata': 'for test-1!'},
                status=201,
            )
        )
        token = ApiOAuth2PersonalTokenFactory(owner=greg)
        token.save()
        auth = {'Authorization': 'Bearer {}'.format(token.token_id)}

        egap_project_path = os.path.join(egap_assets_path, egap_project_name, 'data', 'nonanonymous')

        metadata = recursive_upload(auth, node, egap_project_path)

        assert metadata[0] == {'data': {'attributes': {'path': 'parent'}}}
        assert metadata[1] == {'metadata': 'for test-2!'}
        assert metadata[2] == {'metadata': 'for test-1!'}
