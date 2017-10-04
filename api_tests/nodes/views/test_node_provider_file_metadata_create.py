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
from osf.models import QuickFilesNode
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
    def quickfiles_node(self, user):
        return QuickFilesNode.objects.get_for_user(user)

    @pytest.fixture()
    def quickfiles_file(self, user, quickfiles_node):
        return api_utils.create_test_file(quickfiles_node, user, filename='slippery.mp3')

    @pytest.fixture()
    def quickfiles_folder(self, user, quickfiles_node):
        return quickfiles_node.get_addon('osfstorage').get_root()

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

    # def test_must_have_auth_and_be_contributor(self, app, create_metadata_url, move_payload):
    #     # test_must_have_auth(self, app, file_url):
    #     res = app.post_json_api(create_metadata_url, move_payload, expect_errors=True)
    #     assert res.status_code == 401
    #
    #     # test_must_be_contributor(self, app, file_url):
    #     non_contributor = AuthUserFactory()
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=non_contributor.auth, expect_errors=True)
    #     assert res.status_code == 403
    #
    # def test_move_file_from_root_to_subfolder_and_back(self, app, user, create_metadata_url, move_payload, file, folder, root):
    #     assert len(folder.children) == 0
    #     assert len(root.children) == 2
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 1
    #     assert res.status_code == 200
    #     assert res.json['data']['id'] == file._id
    #     assert res.json['data']['attributes']['name'] == file.name
    #
    #     move_payload['data']['attributes']['destination_parent'] = None
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
    #     assert res.status_code == 200
    #     assert len(folder.children) == 0
    #     assert len(root.children) == 2
    #
    # def test_copy_file_from_root_to_subfolder(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     assert len(folder.children) == 0
    #     assert len(root.children) == 2
    #     res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
    #     assert res.status_code == 201
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 2
    #     assert res.json['data']['id'] == folder.children[0]._id
    #     assert res.json['data']['attributes']['name'] == file.name
    #
    # def test_copy_file_from_subfolder_to_root(self, app, user, create_metadata_url, copy_payload, folder, root):
    #     file2 = folder.append_file("Second file")
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 2
    #
    #     copy_payload['data']['attributes']['destination_parent'] = None
    #     copy_payload['data']['attributes']['source'] = file2._id
    #     res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
    #     assert res.status_code == 201
    #
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 3
    #     assert res.json['data']['id'] != file2._id
    #     assert res.json['data']['attributes']['name'] == file2.name
    #
    # def test_copy_file_to_another_node(self, app, user, create_metadata_url, copy_payload, root, node2_root, node2):
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #     copy_payload['data']['attributes']['destination_node'] = node2._id
    #     copy_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
    #     assert res.status_code == 201
    #     assert len(node2_root.children) == 1
    #     assert len(root.children) == 2
    #
    # def test_move_file_to_another_node(self, app, user, create_metadata_url, move_payload, root, node2_root, node, node2):
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #     move_payload['data']['attributes']['destination_node'] = node2._id
    #     move_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
    #     assert res.status_code == 200
    #     assert len(node2_root.children) == 1
    #     assert len(root.children) == 1
    #
    # def test_copy_file_to_another_node_without_permissions_for_destination_node(self, app, user, create_metadata_url, copy_payload, root, node2_root, node, node2):
    #     user2 = AuthUserFactory()
    #     node.add_contributor(user2, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
    #
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #     copy_payload['data']['attributes']['destination_node'] = node2._id
    #     copy_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, copy_payload, auth=user2.auth, expect_errors=True)
    #     assert res.status_code == 403
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #
    # def test_move_file_to_another_node_without_permissions_for_destination_node(self, app, user, create_metadata_url, move_payload, root, node2_root, node, node2):
    #     user2 = AuthUserFactory()
    #     node.add_contributor(user2, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
    #
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #     move_payload['data']['attributes']['destination_node'] = node2._id
    #     move_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user2.auth, expect_errors=True)
    #     assert res.status_code == 403
    #     assert len(node2_root.children) == 0
    #     assert len(root.children) == 2
    #
    # def test_copy_file_and_change_name(self, app, user, create_metadata_url, copy_payload, file, folder, root):
    #     assert len(folder.children) == 0
    #     assert len(root.children) == 2
    #     assert file.name == "test_file"
    #
    #     copy_payload['data']['attributes']['name'] = "New name"
    #     res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth)
    #     assert res.status_code == 201
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 2
    #     assert res.json['data']['id'] == folder.children[0]._id
    #     assert res.json['data']['attributes']['name'] == "New name"
    #
    #
    # def test_move_file_and_change_name(self, app, user, create_metadata_url, move_payload, file, folder, root):
    #     assert len(folder.children) == 0
    #     assert len(root.children) == 2
    #     assert file.name == "test_file"
    #
    #     move_payload['data']['attributes']['name'] = "New name"
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
    #     assert res.status_code == 200
    #     assert len(folder.children) == 1
    #     assert len(root.children) == 1
    #     assert res.json['data']['id'] == folder.children[0]._id
    #     assert res.json['data']['attributes']['name'] == "New name"
    #
    # def test_move_checked_out_file(self, app, user, create_metadata_url, move_payload, file, folder, root):
    #     file.checkout = user
    #     file.save()
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot move file as it is checked out.' in res._app_iter[0]

    # def test_move_checked_out_file_in_folder(self, app, user, create_metadata_url, move_payload,root):
    #     subfolder = root.append_folder('From Here')
    #     nested_file = subfolder.append_file('No I don\'t wanna go')
    #     nested_file.checkout = user
    #     nested_file.save()
    #
    #     move_payload["data"]["attributes"]["source"] = nested_file._id
    #     move_payload['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot move file as it is checked out.' in res._app_iter[0]

    # def test_move_checked_out_file_in_folder_two_deep(self, app, user, create_metadata_url, move_payload,root):
    #     subfolder = root.append_folder('First Level Folder')
    #     subsubfolder = subfolder.append_folder('Second Level Folder')
    #     nested_file = subsubfolder.append_file('No I don\'t wanna go')
    #     nested_file.checkout = user
    #     nested_file.save()
    #
    #     move_payload["data"]["attributes"]["source"] = nested_file._id
    #     move_payload['destination_parent'] = None
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot move file as it is checked out.' in res._app_iter[0]
    #
    # def test_cannot_move_preprint_file_out_of_node(self, app, user, move_payload, create_metadata_url, root, node, node2, file):
    #     node.preprint_file = file
    #     node.save()
    #
    #     move_payload["data"]["attributes"]["destination_node"] = node2._id
    #     move_payload["data"]["attributes"]["destination_parent"] = None
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot move file as it is the primary file of preprint.' in res._app_iter[0]

    # def test_within_node_move_while_preprint(self, app, user, move_payload, create_metadata_url, root, node, folder, file):
    #     assert len(root.children) == 2
    #     assert len(folder.children) == 0
    #     node.preprint_file = file
    #     node.save()
    #
    #     res = app.post_json_api(create_metadata_url, move_payload, auth=user.auth)
    #     assert res.status_code == 200
    #     assert len(root.children) == 1
    #     assert len(folder.children) == 1

    # def test_cannot_move_file_out_of_quickfiles_node(self, app, user, move_payload, node, quickfiles_node, quickfiles_file, quickfiles_folder):
    #     quickfiles_url = '/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, quickfiles_node._id)
    #
    #     move_payload['data']['attributes']['source'] = quickfiles_file._id
    #     move_payload['data']['attributes']['destination_node'] = node._id
    #     move_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(quickfiles_url, move_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot move file as it is in a quickfiles node.' in res._app_iter[0]
    #
    # def test_can_rename_file_in_quickfiles_node(self, app, user, move_payload, node, quickfiles_node, quickfiles_file, quickfiles_folder):
    #     assert len(quickfiles_folder.children) == 1
    #     quickfiles_url = '/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, quickfiles_node._id)
    #
    #     move_payload['data']['attributes']['source'] = quickfiles_file._id
    #     move_payload['data']['attributes']['destination_parent'] = None
    #     move_payload['data']['attributes']['destination_node'] = quickfiles_node.id
    #     move_payload['data']['attributes']['name'] = "New name"
    #
    #     res = app.post_json_api(quickfiles_url, move_payload, auth=user.auth)
    #     assert res.status_code == 200
    #     assert res.json['data']['attributes']['name'] == 'New name'
    #     assert len(quickfiles_folder.children) == 1

    def test_cannot_rename_file_in_another_quickfiles_node(self, app, user, move_payload, node, quickfiles_node, quickfiles_file, quickfiles_folder):
        non_contributor = AuthUserFactory()
        assert len(quickfiles_folder.children) == 1
        quickfiles_url = '/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, quickfiles_node._id)

        move_payload['data']['attributes']['source'] = quickfiles_file._id
        move_payload['data']['attributes']['destination_parent'] = None
        move_payload['data']['attributes']['destination_node'] = quickfiles_node.id
        move_payload['data']['attributes']['name'] = "New name"

        res = app.post_json_api(quickfiles_url, move_payload, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    # def test_cannot_copy_file_in_quickfiles_node(self, app, user, copy_payload, node,  quickfiles_node, quickfiles_file, quickfiles_folder):
    #     quickfiles_url = '/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, quickfiles_node._id)
    #
    #     copy_payload['data']['attributes']['source'] = quickfiles_file._id
    #     copy_payload['data']['attributes']['destination_node'] = node._id
    #     copy_payload['data']['attributes']['destination_parent'] = None
    #
    #     res = app.post_json_api(quickfiles_url, copy_payload, auth=user.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Cannot copy file as it is in a quickfiles node.' in res._app_iter[0]

    def test_invalid_action(self, app, user, create_metadata_url, copy_payload):
        copy_payload['data']['attributes']['action']= 'burn'
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_invalid_destination_node(self, app, user, create_metadata_url, copy_payload):
        copy_payload['data']['attributes']['destination_node']= '12345'
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_invalid_parent(self, app, user, create_metadata_url, copy_payload, file, folder, root):
        copy_payload['data']['attributes']['destination_node']= '12345'
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_invalid_source(self, app, user, create_metadata_url, copy_payload, file, folder, root):
        copy_payload['data']['attributes']['source']= '12345'
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_invalid_source_node_node(self, app, user, copy_payload, file, folder, root):
        create_metadata_url ='/{}nodes/{}/files/providers/osfstorage/file_metadata/'.format(API_BASE, 12345)
        res = app.post_json_api(create_metadata_url, copy_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_move_file_out_of_registration(self, app, user, create_metadata_url, copy_payload, file, folder, root):
        pass

    def test_copy_file_out_of_registration(self, app, user, create_metadata_url, copy_payload, file, folder, root):
        pass
