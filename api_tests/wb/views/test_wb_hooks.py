from __future__ import unicode_literals

import pytest

from addons.osfstorage.models import OsfStorageFolder
from framework.auth import signing

from api.caching.tasks import update_storage_usage_cache

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PreprintFactory
)
from api_tests.utils import create_test_file, create_test_preprint_file
from osf.models import QuickFilesNode


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def quickfiles_node(user):
    return QuickFilesNode.objects.get_for_user(user)

@pytest.fixture()
def quickfiles_file(user, quickfiles_node):
    file = create_test_file(quickfiles_node, user, filename='road_dogg.mp3')
    return file

@pytest.fixture()
def quickfiles_folder(quickfiles_node):
    return OsfStorageFolder.objects.get_root(target=quickfiles_node)

@pytest.fixture()
def node(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def node_two(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def osfstorage(node):
    return node.get_addon('osfstorage')

@pytest.fixture()
def root_node(osfstorage):
    return osfstorage.get_root()

@pytest.fixture()
def node_two_root_node(node_two):
    node_two_settings = node_two.get_addon('osfstorage')
    return node_two_settings.get_root()

@pytest.fixture()
def file(node, user):
    return create_test_file(node, user, 'test_file')

@pytest.fixture()
def folder(root_node, user):
    return root_node.append_folder('Nina Simone')

@pytest.fixture()
def folder_two(root_node, user):
    return root_node.append_folder('Second Folder')

def sign_payload(payload):
    return signing.sign_data(signing.default_signer, payload)

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestMove():
    @pytest.fixture()
    def move_url(self, node):
        return '/_/wb/hooks/{}/move/'.format(node._id)

    @pytest.fixture()
    def quickfiles_move_url(self, quickfiles_node):
        return '/_/wb/hooks/{}/move/'.format(quickfiles_node._id)

    @pytest.fixture()
    def payload(self, file, folder, root_node, user):
        return {
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        }

    @pytest.fixture()
    def signed_payload(self, payload):
        return sign_payload(payload)

    def test_move_hook(self, app, move_url, signed_payload, folder, file):
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_move_checkedout_file(self, app, file, user, move_url, signed_payload):
        file.checkout = user
        file.save()
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res._app_iter[0]

    def test_move_checked_out_file_in_folder(self, app, root_node, user, folder, folder_two, move_url):
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res.json['errors'][0]['detail']

    def test_move_checkedout_file_two_deep_in_folder(self, app, root_node, user, folder, folder_two, move_url):
        folder_nested = folder.append_folder('Nested')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()

        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res.json['errors'][0]['detail']

    def test_move_file_out_of_node(self, app, user, move_url, root_node, node, node_two, node_two_root_node, folder):
        # project having a preprint should not block other moves
        node.preprint_file = root_node.append_file('far')
        node.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_can_move_file_out_of_quickfiles_node(self, app, quickfiles_move_url, quickfiles_file, quickfiles_node, quickfiles_folder, node, user):
        dest_folder = OsfStorageFolder.objects.get_root(target=node)
        signed_payload = sign_payload({
            'source': quickfiles_folder._id,
            'target': quickfiles_node._id,
            'user': user._id,
            'destination': {
                'parent': dest_folder._id,
                'target': node._id,
                'name': quickfiles_file.name,
            }
        })
        res = app.post_json(quickfiles_move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_can_rename_file_in_quickfiles_node(self, app, node, user, quickfiles_move_url, quickfiles_node, quickfiles_file, quickfiles_folder):
        new_name = 'new_file_name.txt'
        signed_payload = sign_payload({
            'source': quickfiles_file._id,
            'target': quickfiles_node._id,
            'user': user._id,
            'name': quickfiles_file.name,
            'destination': {
                'parent': quickfiles_folder._id,
                'target': quickfiles_node._id,
                'name': new_name,
            }
        })

        res = app.post_json(quickfiles_move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200
        quickfiles_file.reload()
        assert quickfiles_file.name == new_name
        assert res.json['name'] == new_name

    def test_blank_destination_file_name(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': '',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200
        file.reload()
        assert file.name == 'test_file'

    def test_blank_source(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': '',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['source'][0] == 'This field may not be blank.'

    def test_no_parent(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['destination']['parent'][0] == 'This field is required.'

    def test_rename_file(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'new_file_name',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200
        file.reload()
        assert file.name == 'new_file_name'

    def test_invalid_payload(self, app, move_url):
        signed_payload = {
            'key': 'incorrectly_formed_payload'
        }

        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'

    def test_source_does_not_exist(self, app, move_url, root_node, user, folder):
        signed_payload = sign_payload(
            {
                'source': '12345',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404

    def test_parent_does_not_exist(self, app, file, move_url, root_node, user, folder):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': '12345',
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404

    def test_node_in_params_does_not_exist(self, app, file, root_node, user, folder):
        move_url = '/_/wb/hooks/{}/move/'.format('12345')
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404

    def test_storage_usage_move_within_node(self, app, node, signed_payload, move_url):
        """
        Checking moves within a node, since the net value hasn't changed the cache will remain expired at None.
        """
        assert node.storage_usage is None

        res = app.post_json(move_url, signed_payload)

        assert res.status_code == 200
        assert node.storage_usage is None  # this is intentional, the cache shouldn't be touched

    def test_storage_usage_move_between_nodes(self, app, node, node_two, file, root_node, user, node_two_root_node, move_url):
        """
        Checking storage usage when moving files outside a node mean both need to be recalculated, as both values have
        changed.
        """

        assert node.storage_usage is None  # the cache starts expired, but there is 1337 bytes in there
        assert node_two.storage_usage is None  # zero bytes here

        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': node._id,
                'user': user._id,
                'destination': {
                    'parent': node_two_root_node._id,
                    'target': node_two._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload)
        assert res.status_code == 200

        assert node.storage_usage is None
        assert node_two.storage_usage == 1337


@pytest.mark.django_db
class TestMovePreprint():

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def root_node(self, preprint):
        return preprint.root_folder

    @pytest.fixture()
    def file(self, preprint, user):
        return create_test_preprint_file(preprint, user, 'test_file')

    @pytest.fixture()
    def folder(self, root_node, user):
        return root_node.append_folder('Nina Simone')

    @pytest.fixture()
    def move_url(self, preprint):
        return '/_/wb/hooks/{}/move/'.format(preprint._id)

    @pytest.fixture()
    def payload(self, file, folder, root_node, user):
        return {
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        }

    @pytest.fixture()
    def signed_payload(self, payload):
        return sign_payload(payload)

    def test_move_hook(self, app, move_url, signed_payload, folder, file):
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_move_checkedout_file(self, app, file, user, move_url, signed_payload):
        file.checkout = user
        file.save()
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res._app_iter[0]

    def test_move_checked_out_file_in_folder(self, app, root_node, user, folder, folder_two, move_url):
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res.json['errors'][0]['detail']

    def test_move_checkedout_file_two_deep_in_folder(self, app, root_node, user, folder, folder_two, move_url):
        folder_nested = folder.append_folder('Nested')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()

        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert 'Cannot move file as it is checked out.' in res.json['errors'][0]['detail']

    def test_move_primary_file_out_of_node(self, app, user, move_url, root_node, preprint, node_two, node_two_root_node, folder):
        file = folder.append_file('No I don\'t wanna go')
        preprint.primary_file = file
        preprint.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot move file as it is the primary file of preprint.'
    #
    def test_move_file_out_of_node(self, app, user, move_url, root_node, node, node_two, node_two_root_node, folder):
        # project having a preprint should not block other moves
        node.preprint_file = root_node.append_file('far')
        node.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_within_preprint_move(self, app, user, move_url, file, preprint, folder, root_node):
        preprint.primary_file = file
        preprint.save()
        signed_payload = sign_payload({
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        })
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200

    def test_blank_destination_file_name(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': '',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200
        file.reload()
        assert file.name == 'test_file'

    def test_blank_source(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': '',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['source'][0] == 'This field may not be blank.'

    def test_no_parent(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['destination']['parent'][0] == 'This field is required.'

    def test_rename_file(self, app, move_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'new_file_name',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=False)
        assert res.status_code == 200
        file.reload()
        assert file.name == 'new_file_name'

    def test_invalid_payload(self, app, move_url):
        signed_payload = {
            'key': 'incorrectly_formed_payload'
        }

        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'

    def test_source_does_not_exist(self, app, move_url, root_node, user, folder):
        signed_payload = sign_payload(
            {
                'source': '12345',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404

    def test_parent_does_not_exist(self, app, file, move_url, root_node, user, folder):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': '12345',
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404

    def test_preprint_in_params_does_not_exist(self, app, file, root_node, user, folder):
        move_url = '/_/wb/hooks/{}/move/'.format('12345')
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(move_url, signed_payload, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestCopy():
    @pytest.fixture()
    def copy_url(self, node):
        return '/_/wb/hooks/{}/copy/'.format(node._id)

    @pytest.fixture()
    def quickfiles_copy_url(self, quickfiles_node):
        return '/_/wb/hooks/{}/copy/'.format(quickfiles_node._id)

    @pytest.fixture()
    def payload(self, file, folder, root_node, user):
        return {
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        }

    @pytest.fixture()
    def signed_payload(self, payload):
        return sign_payload(payload)

    def test_copy_hook(self, app, copy_url, signed_payload, folder, file):
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_copy_checkedout_file(self, app, file, user, copy_url, signed_payload):
        file.checkout = user
        file.save()
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_checked_out_file_in_folder(self, app, root_node, user, folder, folder_two, copy_url):
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_checkedout_file_two_deep_in_folder(self, app, root_node, user, folder, folder_two, copy_url):
        folder_nested = folder.append_folder('Nested')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()

        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_preprint_file_out_of_node(self, app, user, copy_url, root_node, node, node_two, node_two_root_node, folder):
        file = folder.append_file('No I don\'t wanna go')
        node.preprint_file = file
        node.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_file_out_of_node(self, app, user, copy_url, root_node, node, node_two, node_two_root_node, folder):
        node.preprint_file = root_node.append_file('far')
        node.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_within_node_copy_while_preprint(self, app, user, copy_url, file, node, folder, root_node):
        node.preprint_file = file
        node.save()
        signed_payload = sign_payload({
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_can_copy_file_out_of_quickfiles_node(self, app, quickfiles_copy_url, quickfiles_file, quickfiles_node, quickfiles_folder, node, user):
        dest_folder = OsfStorageFolder.objects.get_root(target=node)
        signed_payload = sign_payload({
            'source': quickfiles_folder._id,
            'target': quickfiles_node._id,
            'user': user._id,
            'destination': {
                'parent': dest_folder._id,
                'target': node._id,
                'name': quickfiles_file.name,
            }
        })
        res = app.post_json(quickfiles_copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_blank_destination_file_name(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': '',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201
        file.reload()
        assert file.name == 'test_file'

    def test_blank_source(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': '',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['source'][0] == 'This field may not be blank.'

    def test_no_parent(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['destination']['parent'][0] == 'This field is required.'

    def test_invalid_payload(self, app, copy_url):
        signed_payload = {
            'key': 'incorrectly_formed_payload'
        }

        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'

    def test_storage_usage_copy_within_node(self, app, node, file, signed_payload, copy_url):
        """
        Checking copys within a node, since the net size will double the storage usage should be the file size * 2
        """
        assert node.storage_usage is None

        res = app.post_json(copy_url, signed_payload)

        assert res.status_code == 201
        assert node.storage_usage == file.versions.last().metadata['size'] * 2

    def test_storage_usage_copy_between_nodes(self, app, node, node_two, file, user, node_two_root_node, copy_url):
        """
        Checking storage usage when copying files to outside a node means only the destination should be recalculated.
        """

        assert node.storage_usage is None  # The node cache starts expired, but there is 1337 bytes in there
        assert node_two.storage_usage is None  # There are zero bytes in node_two

        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': node._id,
                'user': user._id,
                'destination': {
                    'parent': node_two_root_node._id,
                    'target': node_two._id,
                    'name': 'test_file',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload)
        assert res.status_code == 201

        # The node cache is None because it's value should be unchanged --
        assert node.storage_usage is None

        # But there's really 1337 bytes in the node
        update_storage_usage_cache(node._id)
        assert node.storage_usage == 1337

        # And we have exactly 1337 bytes copied in node_two
        assert node_two.storage_usage == 1337


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestCopyPreprint():
    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def root_node(self, preprint):
        return preprint.root_folder

    @pytest.fixture()
    def file(self, preprint, user):
        return create_test_preprint_file(preprint, user, 'test_file')

    @pytest.fixture()
    def folder(self, root_node, user):
        return root_node.append_folder('Nina Simone')

    @pytest.fixture()
    def copy_url(self, preprint):
        return '/_/wb/hooks/{}/copy/'.format(preprint._id)

    @pytest.fixture()
    def payload(self, file, folder, root_node, user):
        return {
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        }

    @pytest.fixture()
    def signed_payload(self, payload):
        return sign_payload(payload)

    def test_copy_hook(self, app, copy_url, signed_payload, folder, file):
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_copy_checkedout_file(self, app, file, user, copy_url, signed_payload):
        file.checkout = user
        file.save()
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_checked_out_file_in_folder(self, app, root_node, user, folder, folder_two, copy_url):
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_checkedout_file_two_deep_in_folder(self, app, root_node, user, folder, folder_two, copy_url):
        folder_nested = folder.append_folder('Nested')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = user
        file.save()

        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_preprint_file_out_of_preprint(self, app, user, copy_url, root_node, preprint, node_two, node_two_root_node, folder):
        file = folder.append_file('No I don\'t wanna go')
        preprint.primary_file = file
        preprint.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 201

    def test_copy_file_out_of_preprint(self, app, user, copy_url, root_node, preprint, node_two, node_two_root_node, folder):
        preprint.primary_file = root_node.append_file('far')
        preprint.save()

        folder_two = node_two_root_node.append_folder('To There')
        signed_payload = sign_payload({
            'source': folder._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder_two._id,
                'target': folder_two.target._id,
                'name': folder_two.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_within_preprint_copy_while_preprint(self, app, user, copy_url, file, preprint, folder, root_node):
        preprint.primary_file = file
        preprint.save()
        signed_payload = sign_payload({
            'source': file._id,
            'target': root_node._id,
            'user': user._id,
            'destination': {
                'parent': folder._id,
                'target': folder.target._id,
                'name': folder.name,
            }
        })
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201

    def test_blank_destination_file_name(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': '',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=False)
        assert res.status_code == 201
        file.reload()
        assert file.name == 'test_file'

    def test_blank_source(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': '',
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['source'][0] == 'This field may not be blank.'

    def test_no_parent(self, app, copy_url, user, root_node, folder, file):
        signed_payload = sign_payload(
            {
                'source': file._id,
                'target': root_node._id,
                'user': user._id,
                'destination': {
                    'target': folder.target._id,
                    'name': 'hello.txt',
                }
            }
        )
        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['destination']['parent'][0] == 'This field is required.'

    def test_invalid_payload(self, app, copy_url):
        signed_payload = {
            'key': 'incorrectly_formed_payload'
        }

        res = app.post_json(copy_url, signed_payload, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'
