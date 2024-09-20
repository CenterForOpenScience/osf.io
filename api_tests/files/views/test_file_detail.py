from urllib.parse import quote, quote_plus

import itsdangerous
from unittest import mock
import pytest
import pytz
from django.utils import timezone
from importlib import import_module
from django.conf import settings as django_conf_settings

from addons.base.utils import get_mfr_url
from addons.github.models import GithubFileNode
from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.listeners import checkin_files_task
from addons.osfstorage.tests.factories import FileVersionFactory
from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf.models import NodeLog, QuickFilesNode, Node, FileVersionUserMetadata
from osf.utils.permissions import WRITE, READ
from osf.utils.workflows import DefaultStates
from osf_tests.factories import (
    AuthUserFactory,
    CommentFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
    PreprintFactory,
)
from website import settings as website_settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore

from addons.base.views import get_authenticated_resource
from framework.exceptions import HTTPError

# stolen from^W^Winspired by DRF
# rest_framework.fields.DateTimeField.to_representation
def _dt_to_iso8601(value):
    iso8601 = value.isoformat()
    if iso8601.endswith('+00:00'):
        iso8601 = iso8601[:-6] + 'Z'  # microsecond precision

    return iso8601


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestFileView:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user, comment_level='public')

    @pytest.fixture()
    def quickfiles_node(self, user):
        return QuickFilesNode.objects.get(creator=user)

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(node, user, create_guid=False)

    @pytest.fixture()
    def file_url(self, file):
        return f'/{API_BASE}files/{file._id}/'

    @pytest.fixture()
    def file_guid_url(self, file):
        return f'/{API_BASE}files/{file.get_guid(create=True)._id}/'

    def test_must_have_auth_and_be_contributor(self, app, file_url):
        # test_must_have_auth(self, app, file_url):
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 401

        # test_must_be_contributor(self, app, file_url):
        non_contributor = AuthUserFactory()
        res = app.get(file_url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    def test_deleted_file_return_410(self, app, node, user):
        deleted_file = api_utils.create_test_file(node, user, create_guid=True)
        url_with_guid = '/{}files/{}/'.format(
            API_BASE, deleted_file.get_guid()._id
        )
        url_with_id = f'/{API_BASE}files/{deleted_file._id}/'

        res = app.get(url_with_guid, auth=user.auth)
        assert res.status_code == 200

        res = app.get(url_with_id, auth=user.auth)
        assert res.status_code == 200

        deleted_file.delete(user=user, save=True)

        res = app.get(url_with_guid, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

        res = app.get(url_with_id, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    def test_file_guid_guid_status(self, app, user, file, file_url):
        # test_unvisited_file_has_no_guid
        res = app.get(file_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['guid'] is None

        # test_visited_file_has_guid
        guid = file.get_guid(create=True)
        res = app.get(file_url, auth=user.auth)
        assert res.status_code == 200
        assert guid is not None
        assert res.json['data']['attributes']['guid'] == guid._id

    def test_file_with_wrong_guid(self, app, user):
        url = f'/{API_BASE}files/{user._id}/'
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    @mock.patch('api.base.throttling.CreateGuidThrottle.allow_request')
    def test_file_guid_not_created_with_basic_auth(
            self, mock_allow, app, user, file_url):
        res = app.get(f'{file_url}?create_guid=1', auth=user.auth)
        guid = res.json['data']['attributes'].get('guid', None)
        assert res.status_code == 200
        assert mock_allow.call_count == 1
        assert guid is None

    @mock.patch('api.base.throttling.CreateGuidThrottle.allow_request')
    def test_file_guid_created_with_cookie(
            self, mock_allow, app, user, file_url, file):
        session = SessionStore()
        session['auth_user_id'] = user._id
        session.create()
        cookie = itsdangerous.Signer(
            website_settings.SECRET_KEY
        ).sign(session.session_key)
        app.set_cookie(website_settings.COOKIE_NAME, cookie.decode())

        res = app.get(f'{file_url}?create_guid=1', auth=user.auth)

        app.reset()  # clear cookie

        assert res.status_code == 200

        guid = res.json['data']['attributes'].get('guid', None)
        assert guid is not None

        assert guid == file.get_guid()._id
        assert mock_allow.call_count == 1

    def test_get_file(self, app, user, file_url, file):
        res = app.get(f'{file_url}?version=2.2', auth=user.auth)
        file.versions.first().reload()
        assert res.status_code == 200
        assert set(res.json.keys()) == {'meta', 'data'}
        attributes = res.json['data']['attributes']
        assert attributes['path'] == file.path
        assert attributes['kind'] == file.kind
        assert attributes['name'] == file.name
        assert attributes['materialized_path'] == file.materialized_path
        assert attributes['last_touched'] is None
        assert attributes['provider'] == file.provider
        assert attributes['size'] == file.versions.first().size
        assert attributes['current_version'] == len(file.history)
        assert attributes['date_modified'] == _dt_to_iso8601(
            file.versions.first().created.replace(tzinfo=pytz.utc)
        )
        assert attributes['date_created'] == _dt_to_iso8601(
            file.versions.last().created.replace(tzinfo=pytz.utc)
        )
        assert attributes['extra']['hashes']['md5'] is None
        assert attributes['extra']['hashes']['sha256'] is None
        assert attributes['tags'] == []
        # make sure download link has a trailing slash
        # so that downloads don't 301
        assert res.json['data']['links']['download'].endswith('/')

        # test_embed_target
        res = app.get(f'{file_url}?embed=target', auth=user.auth)
        assert res.status_code == 200
        embedded_target = res.json['data']['embeds']['target']['data']
        assert embedded_target['id'] == file.target._id
        assert embedded_target['attributes']['title'] == file.target.title

    def test_file_has_rel_link_to_owning_project(
            self, app, user, file_url, node):
        res = app.get(file_url, auth=user.auth)
        assert res.status_code == 200
        assert 'target' in res.json['data']['relationships'].keys()
        expected_url = node.api_v2_url
        actual_url = res.json['data']['relationships']['target']['links']['related']['href']
        assert expected_url in actual_url

    def test_file_has_comments_link(self, app, user, file, file_url):
        file.get_guid(create=True)
        res = app.get(file_url, auth=user.auth)
        assert res.status_code == 200
        assert 'comments' in res.json['data']['relationships'].keys()
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        assert app.get(url, auth=user.auth).status_code == 200
        assert res.json['data']['type'] == 'files'

    def test_file_has_correct_unread_comments_count(
            self, app, user, file, node):
        contributor = AuthUserFactory()
        node.add_contributor(contributor, auth=Auth(user), save=True)
        CommentFactory(
            node=node,
            target=file.get_guid(create=True),
            user=contributor, page='files'
        )
        res = app.get(
            f'/{API_BASE}files/{file._id}/?related_counts=True',
            auth=user.auth
        )
        assert res.status_code == 200
        unread_comments = res.json['data']['relationships']['comments']['links']['related']['meta']['unread']
        assert unread_comments == 1

    def test_only_project_contrib_can_comment_on_closed_project(
            self, app, user, node, file_url):
        node.comment_level = 'private'
        node.is_public = True
        node.save()

        res = app.get(file_url, auth=user.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert res.status_code == 200
        assert can_comment is True

        non_contributor = AuthUserFactory()
        res = app.get(file_url, auth=non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert res.status_code == 200
        assert can_comment is False

    def test_logged_or_not_user_comment_status_on_open_project(
            self, app, node, file_url):
        node.is_public = True
        node.save()

        # test_any_loggedin_user_can_comment_on_open_project(self, app, node,
        # file_url):
        non_contributor = AuthUserFactory()
        res = app.get(file_url, auth=non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert res.status_code == 200
        assert can_comment is True

        # test_non_logged_in_user_cant_comment(self, app, file_url, node):
        res = app.get(file_url)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert res.status_code == 200
        assert can_comment is False

    def test_checkout(self, app, user, file, file_url, node):
        assert file.checkout is None
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth)
        file.reload()
        file.save()
        node.reload()
        assert res.status_code == 200
        assert file.checkout == user

        res = app.get(file_url, auth=user.auth)
        assert node.logs.count() == 2
        assert node.logs.latest().action == NodeLog.CHECKED_OUT
        assert node.logs.latest().user == user
        assert user._id == res.json['data']['relationships']['checkout']['links']['related']['meta']['id']

        assert '/{}users/{}/'.format(
            API_BASE, user._id
        ) in res.json['data']['relationships']['checkout']['links']['related']['href']

        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None
                    }
                }
            }, auth=user.auth)

        file.reload()
        assert file.checkout is None
        assert res.status_code == 200

    def test_checkout_file_error(self, app, user, file_url, file_guid_url, file):
        # test_checkout_file_no_type
        res = app.put_json_api(
            file_url,
            {'data': {'id': file._id, 'attributes': {'checkout': user._id}}},
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400

        # test_checkout_file_no_id
        res = app.put_json_api(
            file_url,
            {'data': {'type': 'files', 'attributes': {'checkout': user._id}}},
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400

        # test_checkout_file_incorrect_type
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'Wrong type.',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # test_checkout_file_incorrect_id
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': '12345',
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # test_use_guid_as_id
        res = app.put_json_api(
            file_guid_url, {
                'data': {
                    'id': file.get_guid(create=True)._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_must_set_self(self, app, user, file, file_url):
        user_unauthorized = UserFactory()
        assert file.checkout is None
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user_unauthorized._id
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        assert res.status_code == 400
        assert file.checkout is None

    def test_must_be_self(self, app, file, file_url):
        user = AuthUserFactory()
        file.checkout = user
        file.save()
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        assert res.status_code == 403
        assert file.checkout == user

    def test_admin_can_checkin(self, app, user, node, file, file_url):
        user_unauthorized = UserFactory()
        node.add_contributor(user_unauthorized)
        file.checkout = user_unauthorized
        file.save()
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        node.reload()
        assert res.status_code == 200
        assert file.checkout is None
        assert node.logs.latest().action == NodeLog.CHECKED_IN
        assert node.logs.latest().user == user

    def test_admin_can_checkout(self, app, user, file_url, file, node):
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        node.reload()
        assert res.status_code == 200
        assert file.checkout == user
        assert node.logs.latest().action == NodeLog.CHECKED_OUT
        assert node.logs.latest().user == user

    def test_cannot_checkin_when_already_checked_in(
            self, app, user, node, file, file_url):
        count = node.logs.count()
        assert not file.is_checked_out
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        node.reload()
        assert res.status_code == 200
        assert node.logs.count() == count
        assert file.checkout is None

    def test_cannot_checkout_when_checked_out(
            self, app, user, node, file, file_url):
        user_unauthorized = UserFactory()
        node.add_contributor(user_unauthorized)
        file.checkout = user_unauthorized
        file.save()
        count = node.logs.count()
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        file.reload()
        node.reload()
        assert res.status_code == 200
        assert file.checkout == user_unauthorized
        assert node.logs.count() == count

    def test_noncontrib_and_read_contrib_cannot_checkout(
            self, app, file, node, file_url):
        # test_noncontrib_cannot_checkout
        non_contrib = AuthUserFactory()
        assert file.checkout is None
        assert not node.has_permission(non_contrib, READ)
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': non_contrib._id
                    }
                }
            }, auth=non_contrib.auth, expect_errors=True, )
        file.reload()
        node.reload()
        assert res.status_code == 403
        assert file.checkout is None
        assert node.logs.latest().action != NodeLog.CHECKED_OUT

        # test_read_contrib_cannot_checkout
        read_contrib = AuthUserFactory()
        node.add_contributor(read_contrib, permissions=READ)
        node.save()
        assert not node.can_edit(user=read_contrib)
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None
                    }
                }
            }, auth=read_contrib.auth, expect_errors=True)
        file.reload()
        assert res.status_code == 403
        assert file.checkout is None
        assert node.logs.latest().action != NodeLog.CHECKED_OUT

    def test_write_contrib_can_checkin(self, app, node, file, file_url):
        write_contrib = AuthUserFactory()
        node.add_contributor(write_contrib, permissions=WRITE)
        node.save()
        assert node.can_edit(user=write_contrib)
        file.checkout = write_contrib
        file.save()
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None
                    }
                }
            }, auth=write_contrib.auth, )
        file.reload()
        assert res.status_code == 200
        assert file.checkout is None

    @mock.patch('addons.osfstorage.listeners.enqueue_postcommit_task')
    def test_removed_contrib_files_checked_in(self, mock_enqueue, app, node, file):
        write_contrib = AuthUserFactory()
        node.add_contributor(write_contrib, permissions=WRITE)
        node.save()
        assert node.can_edit(user=write_contrib)
        file.checkout = write_contrib
        file.save()
        assert file.is_checked_out

        node.remove_contributor(write_contrib, auth=Auth(write_contrib))

        mock_enqueue.assert_called_with(checkin_files_task, (node._id, write_contrib._id,), {}, celery=True)

    def test_must_be_osfstorage(self, app, user, file, file_url):
        file.recast(GithubFileNode._typedmodels_type)
        file.save()
        res = app.put_json_api(
            file_url, {
                'data': {
                    'id': file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': user._id
                    }
                }
            }, auth=user.auth, expect_errors=True, )
        assert res.status_code == 403

    def test_get_file_guids_misc(self, app, user, file, node):
        # test_get_file_resolves_guids
        guid = file.get_guid(create=True)
        url = f'/{API_BASE}files/{guid._id}/'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert set(res.json.keys()) == {'meta', 'data'}
        assert res.json['data']['attributes']['path'] == file.path

        # test_get_file_invalid_guid_gives_404
        url = '/{}files/{}/'.format(API_BASE, 'asdasasd')
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # test_get_file_non_file_guid_gives_404
        url = f'/{API_BASE}files/{node._id}/'
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_current_version_is_equal_to_length_of_history(
            self, app, user, file_url, file):
        res = app.get(file_url, auth=user.auth)
        assert res.json['data']['attributes']['current_version'] == 1
        for version in range(2, 4):
            file.create_version(user, {
                'object': '06d80e' + str(version),
                'service': 'cloud',
                osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
            }, {'size': 1337,
                'contentType': 'img/png'}).save()
            res = app.get(file_url, auth=user.auth)
            assert res.json['data']['attributes']['current_version'] == version

    # Regression test for OSF-7758
    def test_folder_files_relationships_contains_guid_not_id(
            self, app, user, node):
        folder = node.get_addon('osfstorage').get_root(
        ).append_folder('I\'d be a teacher!!')
        folder.save()
        folder_url = f'/{API_BASE}files/{folder._id}/'
        res = app.get(folder_url, auth=user.auth)
        split_href = res.json['data']['relationships']['files']['links']['related']['href'].split(
            '/')
        assert node._id in split_href
        assert node.id not in split_href


@pytest.mark.django_db
class TestFileVersionView:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def osfstorage(self, node):
        return node.get_addon('osfstorage')

    @pytest.fixture()
    def root_node(self, osfstorage):
        return osfstorage.get_root()

    @pytest.fixture()
    def file(self, root_node, user):
        file = root_node.append_file('test_file')
        file.create_version(user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()
        return file

    @pytest.fixture()
    def file_url(self, file):
        return f'/{API_BASE}files/{file._id}/'

    def test_listing(self, app, user, file):
        file.create_version(user, {
            'object': '0683m38e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1347,
            'contentType': 'img/png'
        }).save()

        res = app.get(
            f'/{API_BASE}files/{file._id}/versions/',
            auth=user.auth,
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == '2'
        assert res.json['data'][0]['attributes']['name'] == file.name
        assert res.json['data'][1]['id'] == '1'
        assert res.json['data'][1]['attributes']['name'] == file.name

    def test_load_and_property(self, app, user, file):
        # test_by_id
        res = app.get(
            f'/{API_BASE}files/{file._id}/versions/1/',
            auth=user.auth,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == '1'

        mfr_url = get_mfr_url(file, 'osfstorage')

        render_link = res.json['data']['links']['render']
        download_link = res.json['data']['links']['download']
        assert mfr_url in render_link
        assert quote_plus(download_link) in render_link
        assert quote('revision=1') in render_link

        guid = file.get_guid(create=True)._id
        res = app.get(
            f'/{API_BASE}files/{file._id}/versions/1/',
            auth=user.auth,
        )
        render_link = res.json['data']['links']['render']
        download_link = res.json['data']['links']['download']
        assert mfr_url in render_link
        assert quote_plus(download_link) in render_link
        assert guid in render_link
        assert quote('revision=1') in render_link

        # test_read_only
        assert app.put(
            f'/{API_BASE}files/{file._id}/versions/1/',
            expect_errors=True, auth=user.auth,
        ).status_code == 405

        assert app.post(
            f'/{API_BASE}files/{file._id}/versions/1/',
            expect_errors=True, auth=user.auth,
        ).status_code == 405

        assert app.delete(
            f'/{API_BASE}files/{file._id}/versions/1/',
            expect_errors=True, auth=user.auth,
        ).status_code == 405

    def test_retracted_registration_file(self, app, user, file_url, file):
        resource = RegistrationFactory(is_public=True)
        retraction = resource.retract_registration(
            user=resource.creator,
            justification='Justification for retraction',
            save=True,
            moderator_initiated=False
        )

        retraction.accept()
        resource.save()
        resource.refresh_from_db()

        file.target = resource
        file.save()

        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    def test_retracted_file_returns_410(self, app, user, file_url, file):
        resource = RegistrationFactory(is_public=True)
        retraction = resource.retract_registration(
            user=resource.creator,
            justification='Justification for retraction',
            save=True,
            moderator_initiated=False
        )

        retraction.accept()
        resource.save()
        resource.refresh_from_db()

        file.target = resource
        file.save()

        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    def test_get_authenticated_resource_retracted(self):
        resource = RegistrationFactory(is_public=True)

        assert resource.is_retracted is False

        retraction = resource.retract_registration(
            user=resource.creator,
            justification='Justification for retraction',
            save=True,
            moderator_initiated=False
        )

        retraction.accept()
        resource.save()
        resource.refresh_from_db()

        assert resource.is_retracted is True

        with pytest.raises(HTTPError) as excinfo:
            get_authenticated_resource(resource._id)

        assert excinfo.value.code == 410


@pytest.mark.django_db
class TestFileTagging:

    @pytest.fixture
    def node(self, user, request):
        if request.param == 'project':
            return ProjectFactory(creator=user)
        if request.param == 'registration':
            return RegistrationFactory(creator=user)

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(node, user, filename='file_one')

    @pytest.fixture()
    def payload(self, file):
        payload = {
            'data': {
                'type': 'files',
                'id': file._id,
                'attributes': {
                    'tags': ['goofy']
                }
            }
        }
        if isinstance(file.target, Node):
            payload['data']['attributes']['checkout'] = None
        return payload

    @pytest.fixture()
    def url(self, file):
        return f'/{API_BASE}files/{file._id}/'

    @pytest.mark.parametrize('node', ['registration', 'project'], indirect=True)
    def test_tags_add_and_update_properly(self, app, user, url, payload):
        # test_tags_add_properly
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        # Ensure adding tag data is correct from the PUT response
        assert len(res.json['data']['attributes']['tags']) == 1
        assert res.json['data']['attributes']['tags'][0] == 'goofy'

        # test_tags_update_properly
        # Ensure removing and adding tag data is correct from the PUT response
        payload['data']['attributes']['tags'] = ['goofier']
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1
        assert res.json['data']['attributes']['tags'][0] == 'goofier'

    @pytest.mark.parametrize('node', ['registration', 'project'], indirect=True)
    def test_tags_add_and_remove_properly(self, app, user, url, payload):
        app.put_json_api(url, payload, auth=user.auth)
        payload['data']['attributes']['tags'] = []
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    @pytest.mark.parametrize('node', ['registration', 'project'], indirect=True)
    def test_put_wo_tags_doesnt_remove_tags(self, app, user, url, payload):
        app.put_json_api(url, payload, auth=user.auth)
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        # Ensure adding tag data is correct from the PUT response
        assert len(res.json['data']['attributes']['tags']) == 1
        assert res.json['data']['attributes']['tags'][0] == 'goofy'

    @pytest.mark.parametrize('node', ['registration', 'project'], indirect=True)
    def test_add_and_remove_tag_adds_log(self, app, user, url, payload, node):
        # test_add_tag_adds_log
        count = node.logs.count()
        app.put_json_api(url, payload, auth=user.auth)
        assert node.logs.count() == count + 1
        assert NodeLog.FILE_TAG_ADDED == node.logs.latest().action

        # test_remove_tag_adds_log
        payload['data']['attributes']['tags'] = []
        count = node.logs.count()
        app.put_json_api(url, payload, auth=user.auth)
        assert node.logs.count() == count + 1
        assert NodeLog.FILE_TAG_REMOVED == node.logs.latest().action


@pytest.mark.django_db
class TestPreprintFileView:

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def primary_file(self, preprint):
        return preprint.primary_file

    @pytest.fixture()
    def file_url(self, primary_file):
        return f'/{API_BASE}files/{primary_file._id}/'

    @pytest.fixture()
    def other_user(self):
        return AuthUserFactory()

    def test_published_preprint_file(self, app, file_url, preprint, user, other_user):
        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 200

        # Non contrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 200

        # Write contrib
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 200

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_unpublished_preprint_file(self, app, file_url, preprint, user, other_user):
        preprint.is_published = False
        preprint.save()

        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 200

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_private_preprint_file(self, app, file_url, preprint, user, other_user):
        preprint.is_public = False
        preprint.save()

        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 200

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_deleted_preprint_file(self, app, file_url, preprint, user, other_user):
        preprint.deleted = timezone.now()
        preprint.save()

        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 410

        # Non contrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 410

        # Write contrib
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 410

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    def test_abandoned_preprint_file(self, app, file_url, preprint, user, other_user):
        preprint.machine_state = DefaultStates.INITIAL.value
        preprint.save()

        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_withdrawn_preprint_files(self, app, file_url, preprint, user, other_user):
        preprint.date_withdrawn = timezone.now()
        preprint.save()

        # Unauthenticated
        res = app.get(file_url, expect_errors=True)
        assert res.status_code == 410

        # Noncontrib
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 410

        # Write contributor
        preprint.add_contributor(other_user, WRITE, save=True)
        res = app.get(file_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 410

        # Admin contrib
        res = app.get(file_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 410

@pytest.mark.django_db
class TestShowAsUnviewed:

    @pytest.fixture
    def node(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture
    def test_file(self, user, node):
        test_file = api_utils.create_test_file(node, user, create_guid=False)
        test_file.add_version(FileVersionFactory())
        return test_file

    @pytest.fixture
    def url(self, test_file):
        return f'/{API_BASE}files/{test_file._id}/'

    def test_show_as_unviewed__previously_seen(self, app, user, test_file, url):
        FileVersionUserMetadata.objects.create(
            user=user,
            file_version=test_file.versions.order_by('created').first()
        )

        res = app.get(url, auth=user.auth)
        assert res.json['data']['attributes']['show_as_unviewed']

        FileVersionUserMetadata.objects.create(
            user=user,
            file_version=test_file.versions.order_by('-created').first()
        )

        res = app.get(url, auth=user.auth)
        assert not res.json['data']['attributes']['show_as_unviewed']

    def test_show_as_unviewed__not_previously_seen(self, app, user, test_file, url):
        res = app.get(url, auth=user.auth)
        assert not res.json['data']['attributes']['show_as_unviewed']

    def test_show_as_unviewed__different_user(self, app, user, test_file, url):
        FileVersionUserMetadata.objects.create(
            user=user,
            file_version=test_file.versions.order_by('created').first()
        )
        file_viewer = AuthUserFactory()

        res = app.get(url, auth=file_viewer.auth)
        assert not res.json['data']['attributes']['show_as_unviewed']

    def test_show_as_unviewed__anonymous_user(self, app, test_file, url):
        res = app.get(url)
        assert not res.json['data']['attributes']['show_as_unviewed']

    def test_show_as_unviewed__no_versions(self, app, user, test_file, url):
        # Most Non-OSFStorage providers don't have versions; make sure this still works
        test_file.versions.all().delete()

        res = app.get(url, auth=user.auth)
        assert not res.json['data']['attributes']['show_as_unviewed']
