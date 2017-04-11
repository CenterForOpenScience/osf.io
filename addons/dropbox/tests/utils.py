from contextlib import contextmanager

import mock
from addons.base.tests.base import AddonTestCase, OAuthAddonTestCaseMixin
from addons.dropbox.models import Provider
from addons.dropbox.tests.factories import DropboxAccountFactory


class DropboxAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'dropbox'
    ExternalAccountFactory = DropboxAccountFactory
    Provider = Provider

    def set_node_settings(self, settings):
        super(DropboxAddonTestCase, self).set_node_settings(settings)
        settings.folder = 'foo'
        settings.save()


class MockFileMetadata(object):

    name = 'Prime_Numbers.txt'
    path_display = '/Homework/math/Prime_Numbers.txt'


class MockFolderMetadata(object):

    name = 'math'
    path_display = '/Homework/math'


class MockListFolderResult(object):

    def __init__(self, has_more=False):
        self.entries = [MockFileMetadata(), MockFolderMetadata()]
        self.cursor = 'ZtkX9_EHj3x7PMkVuFIhwKYXEpwpLwyxp9vMKomUhllil9q7eWiAu'
        self.has_more = has_more

class MockName(object):

    display_name = 'Rain Drop, Drop Box'


class MockFullAccount(object):

    name = MockName()


class MockDropbox(object):

    def files_list_folder(self,
            path,
            recursive=False,
            include_media_info=False,
            include_deleted=False,
            include_has_explicit_shared_members=False):
         return MockListFolderResult()

    def files_list_folder_continue(self, cursor):
        return MockListFolderResult()

    def users_get_current_account(self):
        return MockFullAccount()


@contextmanager
def patch_client(target, mock_client=None):
    """Patches a function that returns a DropboxClient, returning an instance
    of MockDropbox instead.

    Usage: ::

        with patch_client('addons.dropbox.view.config.get_client') as client:
            # test view that uses the dropbox client.
    """
    with mock.patch(target) as client_getter:
        client = mock_client or MockDropbox()
        client_getter.return_value = client
        yield client
