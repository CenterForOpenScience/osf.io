# -*- coding: utf-8 -*-
import pytest
from functools import partial
from framework.auth import signing

from api.base.utils import waterbutler_api_url_for

from addons.osfstorage.tests.utils import make_payload, build_payload_v1_logs
from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from addons.base.signals import file_updated

from api.base import utils
from api.base.settings.defaults import API_BASE
from api_tests.utils import disconnected_from_listeners
from api_tests.utils import create_test_quickfile

from django.core.urlresolvers import reverse

from osf.utils.testing.pytest_utils import V1ViewsCase, V2ViewsCase

from osf.models import UserLog
from osf_tests.factories import AuthUserFactory

default_signer = partial(signing.sign_data, signing.default_signer)

signer_does_nothing = lambda payload: payload
signer_unencrypted = lambda payload: {'payload': payload, 'signature': 'wrong', 'time': '99999999999'}
signer_returns_str = lambda payload: str(payload)

signing_expired = partial(signing.sign_data, signing.default_signer, ttl=0)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestFileDetailView(V2ViewsCase):
    """ FileDetailView """

    @pytest.fixture(autouse=True)
    def file_node(self, user, project):
        return create_test_quickfile(user)

    def test_get_files_detail_has_user_relationship(self, app, user, file_node):
        url = '/{}files/{}/'.format(API_BASE, file_node._id)
        res = app.get(url, auth=user.auth)
        file_detail_json = res.json['data']

        assert 'user' in file_detail_json['relationships']
        assert 'node' not in file_detail_json['relationships']
        assert file_detail_json['relationships']['user']['links']['related']['href'].split(
            '/')[-2] == user._id

    def test_embed_user_on_quickfiles_detail(self, app, user, file_node):
        url = '/{}files/{}/?embed=user'.format(API_BASE, file_node._id)
        res = app.get(url, auth=user.auth)

        assert res.json['data'].get('embeds', None)
        assert res.json['data']['embeds']['user']
        assert res.json['data']['embeds']['user']['data']['id'] == user._id


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestQuickFilesV1(V1ViewsCase):

    @pytest.fixture()
    def user(self):
        user = AuthUserFactory()
        user.save()
        file_node = OsfStorageFile(
            name='Pre-existing Quickfile',
            target=user,
            parent=user.quickfolder,
            path='/Pre-existing Quickfile',
            materialized_path='/Pre-existing Quickfile'
        )
        file_node.save()
        return user

    cases = {
        'test_osfstorage_create_child': [{
            # New upload with 201
            'expected': {
                'status': 'success',
                'code': 201
            },
            'uploaded_metadata': {
                'name': 'Test File 1'
            },
        }, {
            # Upload creates new version with 200
            'expected': {
                'status': 'success',
                'code': 200
            },
            'uploaded_metadata': {
                'name': 'Pre-existing Quickfile'
            },
        }, {
            # Uploading folder produces 400
            'expected': {
                'code': 400,
                'error_message': 'You may not create a folder for QuickFolders'
            },
            'uploaded_metadata': {
                'kind': 'folder'
            },
        }, {
            # unsigned payload fails
            'expected': {
                'code': 400,
                'error_message': 'The request payload could not be deserialized.'
            },
            'uploaded_metadata': {'signer': signer_does_nothing},
        }, {
            # unencrypted payload fails
            'expected': {
                'code': 400,
                'error_message': 'The request payload could not be deserialized.'
            },
            'uploaded_metadata': {'signer': signer_unencrypted},
        }, {
            # payload as string fails
            'expected': {
                'code': 400,
                'error_message': 'The request payload could not be deserialized.'
            },
            'uploaded_metadata': {'signer': signer_returns_str},
        }, {
            # payload with expired signature fails
            'expected': {
                'code': 400,
                'error_message': 'Signature has expired.'
            },
            'uploaded_metadata': {'signer': signing_expired},
        }],
    }

    def test_osfstorage_create_child(self, app, user, expected, uploaded_metadata):
        signer = uploaded_metadata.pop('signer', default_signer)
        root_id = user.quickfolder._id
        url = '/api/v1/{}/osfstorage/{}/children/'.format(user._id, root_id)
        payload = make_payload(user, **uploaded_metadata)

        res = app.post_json(url, signer(payload), expect_errors=True)

        assert res.status_code == expected.get('code', 200)

        if res.status_code in (200, 201):
            assert res.json['status'] == expected.get('status')
            assert user.quickfiles.filter(**uploaded_metadata).exists()
        else:
            assert res.json['code'] == res.status_code
            assert res.json['message_long'] == expected.get('error_message')

    def test_osfstorage_get_children(self, app, user):
        root_id = user.quickfolder._id

        url = '/api/v1/{}/osfstorage/{}/children/'.format(user._id, root_id)
        res = app.get(url, default_signer({}))
        assert res.status_code == 200

        _ids = [file['id'] for file in res.json]
        assert list(user.quickfiles.values_list('_id', flat=True)) == _ids
        assert user.quickfiles.filter(name='Pre-existing Quickfile').exists()

    def test_osfstorage_delete(self, app, user):
        file_node = user.quickfiles.first()
        url = '/api/v1/{}/osfstorage/{}/?payload={payload}&signature={signature}'.format(user._id,
                                                                                         file_node._id,
                                                                                         **default_signer({'user': user._id}))

        res = app.delete(url, expect_errors=True)

        assert res.status_code == 200
        assert res.json['status'] == 'success'
        assert file_node not in user.quickfiles.all()


    def test_create_waterbutler_log(self, app, user):
        payload = build_payload_v1_logs(user, metadata={
            'path': 'abc123',
            'materialized': 'pizza',
            'kind': 'file'
        }, provider='osfstorage')

        url = '/api/v1/project/{}/waterbutler/logs/'.format(user._id)
        with disconnected_from_listeners(file_updated):
            resp = app.put_json(url, payload)

        assert resp.status_code == 200
        assert resp.json == {'status': 'success'}

        log = UserLog.objects.first()
        assert UserLog.objects.count() == 1
        assert log.action == 'quickfiles_file_added'
        assert log.params['target'] == user._id

    def test_waterbutler_hook_succeeds_for_quickfiles(self, app, user):
        materialized_path = 'pizza'
        url = user.api_url_for('create_waterbutler_log')
        payload = build_payload_v1_logs(user, metadata={
            'path': 'abc123',
            'materialized': materialized_path,
            'kind': 'file'}, provider='osfstorage')
        resp = app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestQuickFilesWaterButlerHooksV2(V2ViewsCase):

    @pytest.fixture(autouse=True)
    def add_quickfiles(self, user):
        user.quickfolder.append_file('TheElderSproles.txt')

    def test_can_move_file_out_of_quickfolder_v2(self, app, project, user):
        dest_folder = OsfStorageFolder.objects.get_root(target=project)
        quickfile = user.quickfiles.first()

        payload = {
            'source': quickfile._id,
            'target': user._id,
            'user': user._id,
            'destination': {
                'parent': dest_folder._id,
                'node': project._id,
                'target': project._id,
                'name': quickfile.name,
            }
        }
        url = '/_/wb/hooks/{}/move/'.format(user._id)

        res = app.post_json(url, default_signer(payload))
        assert res.status_code == 200

    def test_can_rename_file_in_quickfolder_v2(self, app, user):
        quickfile = user.quickfiles.first()
        new_name = 'Nick Foles'

        payload = {
            'source': quickfile._id,
            'target': user._id,
            'user': user._id,
            'destination': {
                'parent': user.quickfolder._id,
                'node': user._id,
                'target': user._id,
                'name': new_name,
            }
        }
        url = '/_/wb/hooks/{}/move/'.format(user._id)

        res = app.post_json(url, default_signer(payload))
        assert res.status_code == 200
        quickfile.refresh_from_db()
        assert quickfile.name == new_name
        assert res.json['name'] == new_name

    def test_can_copy_file_out_of_quickfolder_v2(self, app, user, project):
        dest_folder = OsfStorageFolder.objects.get_root(target=project)
        quickfile = user.quickfiles.first()

        payload = {
            'source': user.quickfolder._id,
            'target': user._id,
            'user': user._id,
            'destination': {
                'parent': dest_folder._id,
                'node': project._id,
                'target': project._id,
                'name': quickfile.name,
            }
        }
        url = '/_/wb/hooks/{}/copy/'.format(user._id)

        res = app.post_json(url, default_signer(payload))
        assert res.status_code == 201


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestQuickFileMisc:

    @pytest.fixture(autouse=True)
    def add_quickfiles(self, user):
        create_test_quickfile(user, 'Howie Roseman')

    def test_user_quickfiles(self, flask_app, user, user2):
        url = '/profile/{}/'.format(user._id)
        res = flask_app.get(url, auth=user.auth)

        assert u'Quick files' in res.body

        url = '/profile/{}/'.format(user2._id)
        res = flask_app.get(url, auth=user2.auth)

        assert u'Quick files' not in res.body

    @pytest.mark.skip(reason='This points outside the container to Ember and thus fails Travis')
    def test_resolve_guid(self, flask_app, user):
        quickfile = user.quickfiles.first()
        guid = quickfile.get_guid(create=True)._id

        url = '/{}/'.format(guid)
        res = flask_app.get(url, expect_errors=True)

        assert res.status_code == 200
        assert res.request.path == '/{}/'.format(guid)

    def test_deleted_quick_file_gone(self, flask_app, user):
        quickfile = user.quickfiles.first()
        guid = quickfile.get_guid(create=True)._id
        quickfile.delete()

        url = '/{}/'.format(guid)

        res = flask_app.get(url, expect_errors=True)

        assert res.status_code == 410
        assert res.request.path == '/{}/'.format(guid)

    def test_addon_view_or_download_quickfile(self, flask_app, user):
        quickfile = user.quickfiles.first()
        url = '/quickfiles/{}/'.format(quickfile._id)
        res = flask_app.get(url, default_signer({}), expect_errors=True)

        assert res.status_code == 302
        assert 'http://localhost:80/{}/?payload='.format(quickfile.get_guid()._id) in res.location
