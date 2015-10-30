from __future__ import unicode_literals

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from website.addons.osfstorage import settings as osfstorage_settings

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    UserFactory,
    AuthUserFactory
)


class TestFileView(ApiTestCase):
    def setUp(self):
        super(TestFileView, self).setUp()

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

    def test_must_have_auth(self):
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_must_be_contributor(self):
        user = AuthUserFactory()
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_get_file(self):
        res = self.app.get('/{}files/{}/'.format(API_BASE, self.file._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json.keys(), ['data'])
        assert_equal(res.json['data']['attributes'], {
            'path': self.file.path,
            'kind': self.file.kind,
            'name': self.file.name,
            'size': self.file.versions[0].size,
            'provider': self.file.provider,
            'last_touched': None,
        })

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
            {'id': self.file._id, 'attributes': {'checkout': self.user._id}},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_checkout_file_no_id(self):
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'type': 'files', 'attributes': {'checkout': self.user._id}},
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
            {'id': self.file._id, 'type': 'files'},
            auth=self.user.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_must_set_self(self):
        user = UserFactory()
        assert_equal(self.file.checkout, None)
        res = self.app.put_json_api(
            '/{}files/{}/'.format(API_BASE, self.file._id),
            {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': user._id}},
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
            {'id': self.file._id, 'type': 'files', 'attributes': {'checkout': user._id}},
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
