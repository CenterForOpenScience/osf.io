# encoding: utf-8
import os
import shutil
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
    get_egap_assets,
    ensure_egap_schema,
    create_node_from_project_json,
    recursive_upload,
    get_creator_auth_header
)
from api_tests.utils import create_test_file
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
    def node_with_file(self):
        node = NodeFactory()
        file = create_test_file(node, node.creator)
        file.save()
        node.save()
        return node

    @pytest.fixture()
    def egap_assets_path(self):
        return os.path.join(HERE, 'test_directory', 'EGAP')

    @pytest.fixture()
    def zip_data(self, egap_assets_path):
        test_zip_path = os.path.join(egap_assets_path, 'test-egap.zip')
        with open(test_zip_path, 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def egap_project_name(self):
        return '20120220AA'

    def test_get_creator_auth_header(self, greg):
        greg, auth_header = get_creator_auth_header(greg.username)

        gregs_token = ApiOAuth2PersonalToken.objects.get(owner=greg).token_id
        assert auth_header['Authorization'] == 'Bearer {}'.format(gregs_token)

    def test_ensure_egap_schema(self):
        ensure_egap_schema()

        assert RegistrationSchema.objects.get(name='EGAP Registration', schema_version=3)

    def test_create_node_from_project_json(self, egap_assets_path, egap_project_name, greg):
        node = create_node_from_project_json(egap_assets_path, egap_project_name, greg)

        assert node.title == 'Home Security and Infidelity: a case study by Fletcher Cox'
        assert node.creator == greg

        assert len(node.contributors.all()) == 5
        contrib = node.contributors.exclude(username='greg@greg.com').first()
        assert contrib.fullname == 'Fletcher Cox'
        assert node.get_permissions(contrib) == ['read', 'write']
        assert not node.get_visible(greg)

    @responses.activate
    def test_recursive_upload(self, node, greg, egap_assets_path, egap_project_name):
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

        assert metadata[0] == {'metadata': 'for test-2!'}
        assert metadata[1] == {'data': {'attributes': {'path': 'parent'}}}
        assert metadata[2] == {'metadata': 'for test-1!'}

    @responses.activate
    def test_recursive_upload_retry(self, node, greg, egap_assets_path, egap_project_name):
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
                status=500,
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

        assert metadata[0] == {'metadata': 'for test-2!'}
        assert metadata[1] == {'data': {'attributes': {'path': 'parent'}}}
        assert metadata[2] == {'metadata': 'for test-1!'}

    @responses.activate
    def test_get_egap_assets(self, node_with_file, zip_data):
        file_node = node_with_file.files.first()

        responses.add(
            responses.Response(
                responses.GET,
                '{}/v1/resources/{}/providers/osfstorage/{}'.format(
                    WATERBUTLER_INTERNAL_URL,
                    node_with_file._id,
                    file_node._id
                ),
                body=zip_data,
                status=200,
            )
        )

        asset_path = get_egap_assets(node_with_file._id, {'fake auth': 'sadasdadsdasdsds'})
        directory_list = os.listdir(asset_path)
        # __MACOSX is a hidden file created by the os when zipping
        assert set(directory_list) == set(['20110307AA', '__MACOSX', '20110302AA', 'egap_assets.zip', '20120117AA'])

        shutil.rmtree(asset_path)
