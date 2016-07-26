# -*- coding: utf-8 -*-
from nose import tools as nt

from website.models import StoredFileNode
from framework.auth.core import Auth
from website.addons.github.tests.factories import GitHubAccountFactory, GitHubNodeSettingsFactory

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from api_tests.nodes.views.test_node_addons import NodeOAuthAddonTestSuiteMixin

from tests.base import ApiTestCase, ApiAddonTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


class TestFileFiltering(ApiTestCase):
    def setUp(self):
        super(TestFileFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.file1 = api_utils.create_test_file(
            self.node, self.user, filename='file1')
        self.file2 = api_utils.create_test_file(
            self.node, self.user, filename='file2')
        self.file3 = api_utils.create_test_file(
            self.node, self.user, filename='file3')
        self.file4 = api_utils.create_test_file(
            self.node, self.user, filename='file4')

    def test_get_all_files(self):
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/'.format(API_BASE, self.node.pk),
            auth=self.user.auth
        )
        data = res.json.get('data')
        nt.assert_equal(len(data), 4)

    def test_filter_on_tag(self):
        self.file1.add_tag('new', Auth(self.user))
        self.file2.add_tag('new', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, self.node.pk
            ),
            auth=self.user.auth
        )
        data = res.json.get('data')
        nt.assert_equal(len(data), 2)
        names = [f['attributes']['name'] for f in data]
        nt.assert_in('file1', names)
        nt.assert_in('file2', names)

    def test_exclusive_tags(self):
        self.file1.add_tag('news', Auth(self.user))
        self.file2.add_tag('news', Auth(self.user))
        self.file1.add_tag('new', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, self.node.pk
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_query_capitalized(self):
        self.file1.add_tag('new', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=New'.format(
                API_BASE, self.node.pk
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_query_non_capitalized(self):
        self.file1.add_tag('New', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, self.node.pk
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)


class TestFileLists(ApiTestCase):
    def setUp(self):
        super(TestFileLists, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.auth = Auth(self.user)

        self.file_one = api_utils.create_test_file(self.node, self.user, filename="Man I'm the Macho")
        self.file_two = api_utils.create_test_file(self.node, self.user, filename="Like Randy")
        self.file_three = api_utils.create_test_file(self.node, self.user, filename="The choppa go Oscar for Grammy")

        self.checked_in_one = api_utils.create_test_file(self.node, self.user, filename="Hey neighbor its kinda sandy")
        self.checked_in_two = api_utils.create_test_file(self.node, self.user, filename="I hope yall understand me")
        self.checked_in_one.checkout = self.user
        self.checked_in_two.checkout = self.user
        self.checked_in_one.save()
        self.checked_in_two.save()

    def test_bulk_checkout(self):
        nt.assert_equal(self.file_one.checkout, None)
        nt.assert_equal(self.file_two.checkout, None)

        bulk_file_payload = {
            'data': [
                {
                    'id': self.file_one._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': self.user._id,
                    }
                },
                {
                    'id': self.file_two._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': self.user._id,
                    }
                }
            ]
        }

        res = self.app.put_json_api(
            '/{}files/{}/list/osfstorage/'.format(
                API_BASE, self.node.pk
            ),
            bulk_file_payload,
            auth=self.user.auth,
            bulk=True
        )

        nt.assert_equal(res.status_code, 200)

        self.file_one.reload()
        self.file_two.reload()

        nt.assert_equal(self.file_one.checkout, self.user)
        nt.assert_equal(self.file_two.checkout, self.user)

    def test_bulk_checkin(self):
        nt.assert_equal(self.checked_in_one.checkout, self.user)
        nt.assert_equal(self.checked_in_two.checkout, self.user)

        bulk_file_payload = {
            'data': [
                {
                    'id': self.checked_in_one._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None,
                    }
                },
                {
                    'id': self.checked_in_two._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None,
                    }
                }
            ]
        }

        res = self.app.put_json_api(
            '/{}files/{}/list/osfstorage/'.format(
                API_BASE, self.node.pk
            ),
            bulk_file_payload,
            auth=self.user.auth,
            bulk=True
        )

        nt.assert_equal(res.status_code, 200)

        self.checked_in_one.reload()
        self.checked_in_two.reload()

        nt.assert_equal(self.checked_in_one.checkout, None)
        nt.assert_equal(self.checked_in_two.checkout, None)

    def test_admin_forced_checkin(self):
        """
        Test to see if an admin can bulk check in files that a user has checked out
        """
        admin = AuthUserFactory()
        self.node.add_contributor(admin, auth=self.auth, permissions=['read', 'write', 'admin'])
        self.node.save()

        nt.assert_equal(self.checked_in_one.checkout, self.user)
        nt.assert_equal(self.checked_in_two.checkout, self.user)

        bulk_file_payload = {
            'data': [
                {
                    'id': self.checked_in_one._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None,
                    }
                },
                {
                    'id': self.checked_in_two._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': None,
                    }
                }
            ]
        }

        res = self.app.put_json_api(
            '/{}files/{}/list/osfstorage/'.format(
                API_BASE, self.node.pk
            ),
            bulk_file_payload,
            auth=admin.auth,
            bulk=True
        )

        nt.assert_equal(res.status_code, 200)

        self.checked_in_one.reload()
        self.checked_in_two.reload()

        nt.assert_equal(self.checked_in_one.checkout, None)
        nt.assert_equal(self.checked_in_two.checkout, None)


class TestFileListWithAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'github'
    AccountFactory = GitHubAccountFactory
    NodeSettingsFactory = GitHubNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }

    def test_bulk_checkout_non_osfstorage(self):
        """Right now, only osfstorage should  be allowed for the API bulk file checkout endpoint.
        An error should be returned if the API is attempted for a file outside of osfstorage
        """
        github_file = api_utils.create_test_file(self.node, self.user, create_guid=False, filename="panda")
        github_file.provider = 'github'
        github_file.save()

        github_file_two = api_utils.create_test_file(self.node, self.user, create_guid=False, filename="panda panda panda")
        github_file_two.provider = 'github'
        github_file_two.save()

        nt.assert_equal(github_file.checkout, None)
        nt.assert_equal(github_file_two.checkout, None)

        bulk_file_payload = {
            'data': [
                {
                    'id': github_file._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': self.user._id,
                    }
                },
                {
                    'id': github_file_two._id,
                    'type': 'files',
                    'attributes': {
                        'checkout': self.user._id,
                    }
                }
            ]
        }

        res = self.app.put_json_api(
            '/{}files/{}/list/github/'.format(
                API_BASE, self.node.pk
            ),
            bulk_file_payload,
            auth=self.user.auth,
            bulk=True,
            expect_errors=True
        )

        nt.assert_equal(res.status_code, 403)

        nt.assert_equal(github_file.checkout, None)
        nt.assert_equal(github_file_two.checkout, None)
