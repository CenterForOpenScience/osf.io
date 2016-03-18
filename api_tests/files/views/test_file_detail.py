from __future__ import unicode_literals

import pytz
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from website.addons.osfstorage import settings as osfstorage_settings

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    UserFactory,
    AuthUserFactory,
    CommentFactory
)


# stolen from^W^Winspired by DRF rest_framework.fields.DateTimeField.to_representation
def _dt_to_iso8601(value):
    iso8601 = value.isoformat()
    if iso8601.endswith('+00:00'):
        iso8601 = iso8601[:-9] + 'Z'  # offset upped to 9 to get rid of 3 ms decimal points

    return iso8601

class TestFileView(ApiTestCase):
    def setUp(self):
        super(TestFileView, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.file = api_utils.create_test_file(self.node, self.user)

    def test_must_have_auth(self):
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_must_be_contributor(self):
        user = AuthUserFactory()
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_get_file(self):
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), auth=self.user.auth)
        self.file.versions[-1]._clear_caches()
        self.file.versions[-1].reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json.keys(), ['data'])
        assert_equal(res.json['data']['attributes'], {
            'path': self.file.path,
            'kind': self.file.kind,
            'name': self.file.name,
            'materialized_path': self.file.materialized_path,
            'last_touched': None,
            'provider': self.file.provider,
            'size': self.file.versions[-1].size,
            # HACK: odm's dates are weird
            'date_modified': _dt_to_iso8601(self.file.versions[-1].date_created.replace(tzinfo=pytz.utc)),
            'date_created': _dt_to_iso8601(self.file.versions[0].date_created.replace(tzinfo=pytz.utc)),
            'extra': {
                'hashes': {
                    'md5': None,
                    'sha256': None,
                },
            },
        })

    def test_file_has_comments_link(self):
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('comments', res.json['data']['relationships'].keys())
        expected_url = '/{}nodes/{}/comments/?filter[target]={}'.format(API_BASE, self.node._id, self.file.get_guid()._id)
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        assert_in(expected_url, url)

    def test_file_has_correct_unread_comments_count(self):
        contributor = AuthUserFactory()
        self.node.add_contributor(contributor, auth=Auth(self.user), save=True)
        comment = CommentFactory(node=self.node, target=self.file.get_guid(), user=contributor, page='files')
        res = self.app.get('/{}files/{}/?related_counts=True'.format(API_BASE, self.file._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        unread_comments = res.json['data']['relationships']['comments']['links']['related']['meta']['unread']
        assert_equal(unread_comments, 1)

    def test_checkout(self):
        assert_equal(self.file.checkout, None)
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth
        )
        self.file.reload()
        assert_equal(res.status_code, 200)
        assert_equal(self.file.checkout, self.user)

        res = self.app.get(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            auth=self.user.auth
        )
        assert_equal(
            self.user._id,
            res.json['data']['relationships']['checkout']['links']['related']['meta']['id']
        )
        assert_in(
            '/{}users/{}/'.format(API_BASE, self.user._id),
            res.json['data']['relationships']['checkout']['links']['related']['href']
        )

        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': None}}},
            auth=self.user.auth
        )
        self.file.reload()
        assert_equal(self.file.checkout, None)
        assert_equal(res.status_code, 200)

    def test_checkout_file_no_type(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_checkout_file_no_id(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'type': 'files', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_checkout_file_incorrect_type(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'Wrong type.', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_checkout_file_incorrect_id(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': '12345', 'type': 'files', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_checkout_file_no_attributes(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files'}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_must_set_self(self):
        user = UserFactory()
        assert_equal(self.file.checkout, None)
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': user._id}}},
            auth=self.user.auth,
            expect_errors=True,
        )
        self.file.reload()
        assert_equal(res.status_code, 400)
        assert_equal(self.file.checkout, None)

    def test_must_be_self(self):
        user = AuthUserFactory()
        self.file.checkout = self.user
        self.file.save()
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': user._id}}},
            auth=user.auth,
            expect_errors=True,
        )
        self.file.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.file.checkout, self.user)

    def test_admin_can_checkin(self):
        user = UserFactory()
        self.node.add_contributor(user)
        self.file.checkout = user
        self.file.save()
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': None}}},
            auth=self.user.auth,
            expect_errors=True,
        )
        self.file.reload()
        assert_equal(res.status_code, 200)
        assert_equal(self.file.checkout, None)

    def test_admin_can_checkout(self):
        user = UserFactory()
        self.node.add_contributor(user)
        self.file.checkout = user
        self.file.save()
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth,
            expect_errors=True,
        )
        self.file.reload()
        assert_equal(res.status_code, 200)
        assert_equal(self.file.checkout, self.user)

    def test_user_can_checkin(self):
        user = AuthUserFactory()
        self.node.add_contributor(user, permissions=['read', 'write'])
        self.node.save()
        assert_true(self.node.can_edit(user=user))
        self.file.checkout = user
        self.file.save()
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': None}}},
            auth=user.auth,
        )
        self.file.reload()
        assert_equal(res.status_code, 200)
        assert_equal(self.file.checkout, None)

    def test_must_be_osfstorage(self):
        self.file.provider = 'github'
        self.file.save()
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'data': {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': self.user._id}}},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 403)


class TestFileVersionView(ApiTestCase):
    def setUp(self):
        super(TestFileVersionView, self).setUp()

        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

        self.osfstorage = self.node.get_addon('osfstorage')

        self.root_node = self.osfstorage.get_root()
        self.file = self.root_node.append_file('test_file')
        self.file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()

    def test_listing(self):
        self.file.create_version(self.user, {
            'object': '0683m38e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1347,
            'contentType': 'img/png'
        }).save()

        res = self.app.get(
            '/{}files/{}/versions/'.format(API_BASE, self.file._id),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], '1')
        assert_equal(res.json['data'][1]['id'], '2')

    def test_by_id(self):
        res = self.app.get(
            '/{}files/{}/versions/1/'.format(API_BASE, self.file._id),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], '1')

    def test_read_only(self):
        assert_equal(self.app.put(
            '/{}files/{}/versions/1/'.format(API_BASE, self.file._id),
            expect_errors=True,
            auth=self.user.auth,
        ).status_code, 405)

        assert_equal(self.app.post(
            '/{}files/{}/versions/1/'.format(API_BASE, self.file._id),
            expect_errors=True,
            auth=self.user.auth,
        ).status_code, 405)

        assert_equal(self.app.delete(
            '/{}files/{}/versions/1/'.format(API_BASE, self.file._id),
            expect_errors=True,
            auth=self.user.auth,
        ).status_code, 405)
