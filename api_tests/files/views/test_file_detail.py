from __future__ import unicode_literals

import itsdangerous
import mock
import pytest
import pytz

from addons.github.models import GithubFileNode
from addons.osfstorage import settings as osfstorage_settings
from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf.models import NodeLog, Session, QuickFilesNode
from osf_tests.factories import (
    AuthUserFactory,
    CommentFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import capture_signals
from website import settings as website_settings
from website.project.signals import contributor_removed


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
    def file(self, user, node):
        return api_utils.create_test_file(node, user, create_guid=False)

    @pytest.fixture()
    def file_url(self, file):
        return '/{}files/{}/'.format(API_BASE, file._id)

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
        url_with_id = '/{}files/{}/'.format(API_BASE, deleted_file._id)

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

    @mock.patch('api.base.throttling.CreateGuidThrottle.allow_request')
    def test_file_guid_not_created_with_basic_auth(
            self, mock_allow, app, user, file_url):
        res = app.get('{}?create_guid=1'.format(file_url), auth=user.auth)
        guid = res.json['data']['attributes'].get('guid', None)
        assert res.status_code == 200
        assert mock_allow.call_count == 1
        assert guid is None

    @mock.patch('api.base.throttling.CreateGuidThrottle.allow_request')
    def test_file_guid_created_with_cookie(
            self, mock_allow, app, user, file_url, file):
        session = Session(data={'auth_user_id': user._id})
        session.save()
        cookie = itsdangerous.Signer(
            website_settings.SECRET_KEY
        ).sign(session._id)
        app.set_cookie(website_settings.COOKIE_NAME, str(cookie))

        res = app.get('{}?create_guid=1'.format(file_url), auth=user.auth)

        app.reset()  # clear cookie

        assert res.status_code == 200

        guid = res.json['data']['attributes'].get('guid', None)
        assert guid is not None

        assert guid == file.get_guid()._id
        assert mock_allow.call_count == 1

    def test_get_file(self, app, user, file_url, file):
        res = app.get(file_url, auth=user.auth)
        file.versions.first().reload()
        assert res.status_code == 200
        assert res.json.keys() == ['meta', 'data']
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

    def test_file_has_rel_link_to_owning_project(
            self, app, user, file_url, node):
        res = app.get(file_url, auth=user.auth)
        assert res.status_code == 200
        assert 'node' in res.json['data']['relationships'].keys()
        expected_url = node.api_v2_url
        actual_url = res.json['data']['relationships']['node']['links']['related']['href']
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
            '/{}files/{}/?related_counts=True'.format(API_BASE, file._id),
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

    def test_checkout_file_error(self, app, user, file_url, file):
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

        # test_checkout_file_no_attributes
        res = app.put_json_api(
            file_url,
            {'data': {'id': file._id, 'type': 'files'}},
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400

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
        assert not node.has_permission(non_contrib, 'read')
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
        node.add_contributor(read_contrib, permissions=['read'])
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
        node.add_contributor(write_contrib, permissions=['read', 'write'])
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

    def test_removed_contrib_files_checked_in(self, app, node, file):
        write_contrib = AuthUserFactory()
        node.add_contributor(write_contrib, permissions=['read', 'write'])
        node.save()
        assert node.can_edit(user=write_contrib)
        file.checkout = write_contrib
        file.save()
        assert file.is_checked_out
        with capture_signals() as mock_signals:
            node.remove_contributor(write_contrib, auth=Auth(write_contrib))
        assert mock_signals.signals_sent() == set([contributor_removed])
        file.reload()
        assert not file.is_checked_out

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
        url = '/{}files/{}/'.format(API_BASE, guid._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json.keys() == ['meta', 'data']
        assert res.json['data']['attributes']['path'] == file.path

        # test_get_file_invalid_guid_gives_404
        url = '/{}files/{}/'.format(API_BASE, 'asdasasd')
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # test_get_file_non_file_guid_gives_404
        url = '/{}files/{}/'.format(API_BASE, node._id)
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
        folder_url = '/{}files/{}/'.format(API_BASE, folder._id)
        res = app.get(folder_url, auth=user.auth)
        split_href = res.json['data']['relationships']['files']['links']['related']['href'].split(
            '/')
        assert node._id in split_href
        assert node.id not in split_href

    def test_embed_user_on_quickfiles_detail(self, app, user):
        quickfiles = QuickFilesNode.objects.get(creator=user)
        osfstorage = quickfiles.get_addon('osfstorage')
        root = osfstorage.get_root()
        test_file = root.append_file('speedyfile.txt')

        url = '/{}files/{}/?embed=user'.format(API_BASE, test_file._id)
        res = app.get(url, auth=user.auth)

        assert res.json['data'].get('embeds', None)
        assert res.json['data']['embeds'].get('user')
        assert res.json['data']['embeds']['user']['data']['id'] == user._id


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
            '/{}files/{}/versions/'.format(API_BASE, file._id),
            auth=user.auth,
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == '2'
        assert res.json['data'][1]['id'] == '1'

    def test_load_and_property(self, app, user, file):
        # test_by_id
        res = app.get(
            '/{}files/{}/versions/1/'.format(API_BASE, file._id),
            auth=user.auth,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == '1'

        # test_read_only
        assert app.put(
            '/{}files/{}/versions/1/'.format(API_BASE, file._id),
            expect_errors=True, auth=user.auth,
        ).status_code == 405

        assert app.post(
            '/{}files/{}/versions/1/'.format(API_BASE, file._id),
            expect_errors=True, auth=user.auth,
        ).status_code == 405

        assert app.delete(
            '/{}files/{}/versions/1/'.format(API_BASE, file._id),
            expect_errors=True, auth=user.auth,
        ).status_code == 405


@pytest.mark.django_db
class TestFileTagging:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file_one(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_one')

    @pytest.fixture()
    def payload(self, file_one):
        payload = {
            'data': {
                'type': 'files',
                'id': file_one._id,
                'attributes': {
                    'checkout': None,
                    'tags': ['goofy']
                }
            }
        }
        return payload

    @pytest.fixture()
    def url(self, file_one):
        return '/{}files/{}/'.format(API_BASE, file_one._id)

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

    def test_tags_add_and_remove_properly(self, app, user, url, payload):
        app.put_json_api(url, payload, auth=user.auth)
        payload['data']['attributes']['tags'] = []
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    def test_put_wo_tags_doesnt_remove_tags(self, app, user, url, payload):
        app.put_json_api(url, payload, auth=user.auth)
        payload['data']['attributes'] = {'checkout': None}
        res = app.put_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        # Ensure adding tag data is correct from the PUT response
        assert len(res.json['data']['attributes']['tags']) == 1
        assert res.json['data']['attributes']['tags'][0] == 'goofy'

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
