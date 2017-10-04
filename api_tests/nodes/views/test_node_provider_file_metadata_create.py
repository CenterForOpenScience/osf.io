from __future__ import unicode_literals

import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
)
from website.util import permissions


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeProviderFileMetadataCreateView:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def node2(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(node, user, create_guid=False)

    @pytest.fixture()
    def root(self, node):
        return node.get_addon('osfstorage').get_root()

    @pytest.fixture()
    def node2_root(self, node2):
        return node2.get_addon('osfstorage').get_root()

    @pytest.fixture()
    def folder(self, root):
        folder = root.append_folder('Test folder')
        folder.save()
        return folder

    @pytest.fixture()
    def create_metadata_url(self, node):
        return '/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, node._id)

    @pytest.fixture()
    def move_payload(self, file, folder):
        return {
            "data": {
                "type": "file_metadata",
                "attributes": {
                    "action": "move",
                    "destination_parent": folder._id,
                    "source": file._id,
                }
            }
        }

    @pytest.fixture()
    def copy_payload(self, file, folder):
        return {
            "data": {
                "type": "file_metadata",
                "attributes": {
                    "action": "copy",
                    "destination_parent": folder._id,
                    "source": file._id,
                }
            }
        }

    def test_must_have_auth_and_be_contributor(self, app, create_metadata_url, move_payload):
        # test_must_have_auth(self, app, file_url):
        res = app.post_json_api(create_metadata_url, move_payload, expect_errors=True)
        assert res.status_code == 401

        # test_must_be_contributor(self, app, file_url):
        non_contributor = AuthUserFactory()
        res = app.post_json_api(create_metadata_url, move_payload, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    def test_move_file_from_root_to_subfolder_and_back(self, app, user, create_metadata_url, move_payload, file, folder, root):
        assert len(folder.children) == 0
        assert len(root.children) == 2

        res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
        assert len(folder.children) == 1
        assert len(root.children) == 1
        assert res.status_code == 200
        assert res.json['data']['id'] == file._id
        assert res.json['data']['attributes']['name'] == file.name

        move_payload['data']['attributes']['destination_parent'] = None
        res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
        assert res.status_code == 200
        assert len(folder.children) == 0
        assert len(root.children) == 2

    def test_copy_file_from_root_to_subfolder(self, app, user, create_metadata_url, copy_payload, file, folder, root):
        assert len(folder.children) == 0
        assert len(root.children) == 2
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
        assert res.status_code == 201
        assert len(folder.children) == 1
        assert len(root.children) == 2
        assert res.json['data']['id'] == folder.children[0]._id
        assert res.json['data']['attributes']['name'] == file.name

    def test_copy_file_from_subfolder_to_root(self, app, user, create_metadata_url, copy_payload, folder, root):
        file2 = folder.append_file("Second file")
        assert len(folder.children) == 1
        assert len(root.children) == 2

        copy_payload['data']['attributes']['destination_parent'] = None
        copy_payload['data']['attributes']['source'] = file2._id
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
        assert res.status_code == 201

        assert len(folder.children) == 1
        assert len(root.children) == 3
        assert res.json['data']['id'] != file2._id
        assert res.json['data']['attributes']['name'] == file2.name

    def test_copy_file_to_another_node(self, app, user, create_metadata_url, copy_payload, root, node2_root, node2):
        assert len(node2_root.children) == 0
        assert len(root.children) == 2
        copy_payload['data']['attributes']['destination_node'] = node2._id
        copy_payload['data']['attributes']['destination_parent'] = None

        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
        assert res.status_code == 201
        assert len(node2_root.children) == 1
        assert len(root.children) == 2

    def test_copy_file_to_another_node_without_permissions(self, app, user, create_metadata_url, copy_payload, root, node2_root, node, node2):
        user2 = AuthUserFactory()
        node.add_contributor(user2, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)

        assert len(node2_root.children) == 0
        assert len(root.children) == 2
        copy_payload['data']['attributes']['destination_node'] = node2._id
        copy_payload['data']['attributes']['destination_parent'] = None

        res = app.post_json_api(create_metadata_url, copy_payload, auth=user2.auth, expect_errors=True)
        assert res.status_code == 403
        assert len(node2_root.children) == 0
        assert len(root.children) == 2

    # def test_move_file_to_another_node(self, app, user, create_metadata_url, move_payload, file, folder, root):
    #     pass
    #
    # def test_copy_file_and_change_name(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_file_and_change_name(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_file_in_quickfiles_node(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_copy_file_in_quickfiles_node(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_file_into_location_where_it_already_exists(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_copy_file_into_location_where_it_already_exists(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_primary_preprint_file(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_checked_out_file(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_invalid_action(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_invalid_node(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_invalid_source(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_invalid_destination_node(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_move_file_out_of_registration(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
    #
    # def test_copy_file_out_of_registration(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     pass
