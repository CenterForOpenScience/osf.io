import os
import json
import pytest
import responses

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    ApiOAuth2PersonalTokenFactory
)


from scripts.add_users_to_nodes import (
    add_contributor,
    get_file_from_guid
)

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.django_db
class TestAddUsersToNodes:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def token(self, user):
        return ApiOAuth2PersonalTokenFactory(owner=user).token_id

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def file_metadata_response(self):
        with open(os.path.join(HERE, 'fixtures/file-metadata-response.json'), 'rb') as fp:
            return json.loads(fp.read())

    @responses.activate
    def test_add_contributor(self, user, token, node, contrib):
        responses.add(
            responses.Response(
                responses.POST,
                'http://localhost:8000/v2/nodes/{}/contributors/?send_email=false'.format(node._id),
            )
        )
        add_contributor(node._id, token, contrib._id)
        request_data = json.loads(responses.calls[0].request.body)

        assert request_data['data']['relationships']['users']['data']['id'] == contrib._id

    @responses.activate
    def test_get_file_from_guid(self, user, token, node, contrib, file_metadata_response):
        responses.add(
            responses.Response(
                responses.GET,
                'http://192.168.168.167:8000/v2/nodes/{}/files/osfstorage/'.format(node._id),
                json=file_metadata_response

            )
        )
        responses.add(
            responses.Response(
                responses.GET,
                'http://localhost:7777/v1/resources/pkh86/providers/osfstorage/5e163cc3d2562900787f6c65'.format(node._id),
                body=b'File data'
            )
        )
        data = get_file_from_guid(token, node._id, 'filename.tsv')

        assert data.read() == b'File data'
