import base64
from datetime import datetime
import os
from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException
from website import settings
from website.addons.citations.utils import serialize_account, serialize_folder
from website.addons.base import AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase, GuidFile
from website.addons.googledrive import exceptions
from website.addons.googledrive.serializer import GoogleDriveSerializer
from website.oauth.models import ExternalProvider
from .client import GoogleAuthClient, GoogleDriveClient
from . import settings as drive_settings

class GoogleDriveGuidFile(GuidFile):
    path = fields.StringField(index=True)

    @property
    def waterbutler_path(self):
        return self.path.replace(self.folder, '', 1)

    @property
    def provider(self):
        return 'googledrive'

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def file_name(self):
        if self.revision:
            return '{0}_{1}_{2}.html'.format(self._id, self.revision, base64.b64encode(self.folder))
        return '{0}_{1}_{2}.html'.format(self._id, self.unique_identifier, base64.b64encode(self.folder))

    @property
    def mfr_temp_path(self):
        """Files names from Google Docs metadata doesn't necessarily correspond
        to download file names. Use the `downloadExt` field in the Docs metadata
        to save the temporary file with the appropriate extension.
        """
        ext = (
            self._metadata_cache['extra'].get('downloadExt') or
            os.path.splitext(self.name)[-1]
        )
        return os.path.join(
            settings.MFR_TEMP_PATH,
            self.node._id,
            self.provider,
            # Attempt to keep the original extension of the file for MFR detection
            self.file_name + ext,
        )

    @property
    def folder(self):
        folder = self.node.get_addon('googledrive').folder_path
        if folder == '/':
            return ''
        return '/' + folder

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['revisionId']

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record. Return a tuple of the form (obj, created)
        """
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, path=path)
            new.save()
            created = True
        return new, created


class GoogleDriveProvider(ExternalProvider):
    name = 'Google Drive'
    short_name = 'googledrive'

    client_id = drive_settings.CLIENT_ID
    client_secret = drive_settings.CLIENT_SECRET

    auth_url_base = "https://accounts.google.com/o/oauth2/auth?access_type=offline&approval_prompt=force"
    callback_url = 'https://www.googleapis.com/oauth2/v3/token'

    default_scopes = drive_settings.OAUTH_SCOPE
    _auth_client = GoogleAuthClient()
    _drive_client = GoogleDriveClient()

    def handle_callback(self, response):
        client = self._auth_client
        info = client.userinfo(response['access_token'])
        #TODO(kush): Remove this if else loop. Used only for debugging
        if 'KushagraGuptaKG' in info['profile']:
            display_name = info['name'] + '[GMAIL]'
        else:
            display_name = info['name'] + '[RIT]'
        return {
            'provider_id': info['sub'],
            'display_name': display_name,
            'profile_url': info['profile']
        }

    def _get_folders(self):
        """ Get a list of a user's folders"""
        client = self._drive_client
        return client.folders()


    def _refresh_token(self, access_token, refresh_token):
        client = self._auth_client
        token = client.refresh(access_token, refresh_token)
        return token


class GoogleDriveUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = GoogleDriveProvider
    oauth_grants = fields.DictionaryField()
    serializer = GoogleDriveSerializer
    #
    # def _get_connected_accounts(self):
    #     """ Get user's connected Google Drive accounts"""
    #     return [
    #         x for x in self.owner.external_accounts if x.provider == 'googledrive'
    #     ]
    #
    #
    # # using citations/utils for now. Should be generalized to addons/utils
    # def to_json(self, user):
    #     ret = super(GoogleDriveUserSettings, self).to_json(user)
    #
    #     ret['accounts'] = [
    #         serialize_account(each)
    #         for each in self._get_connected_accounts()
    #     ]
    #     return ret


class GoogleDriveNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = GoogleDriveProvider

    drive_folder_id = fields.StringField()
    drive_folder_name = fields.StringField()
    folder_path = fields.StringField()
    serializer = GoogleDriveSerializer

    _api = None

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = GoogleDriveProvider()
            self._api.account = self.external_account
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.drive_folder_id}
        ))

    def set_folder(self, folder, auth, add_log=True):
        self.drive_folder_id= folder['id']
        self.folder_path = folder['path']


    # using citations/utils for now. Should be generalized to addons/utils
    # TODO: Why am I used?
    @property
    def root_folder(self):
        root = serialize_folder(
            'All Documents',
            id='root',
            parent_id='__'
        )
        root['kind'] = 'folder'
        return root

    @property
    def provider_name(self):
        return 'googledrive'

    def clear_auth(self):
        self.drive_folder_id = None
        self.folder_path = None
        self.drive_folder_name = None
        return super(GoogleDriveNodeSettings, self).clear_auth()

    def set_auth(self, *args, **kwargs):
        self.drive_folder_id = None
        return super(GoogleDriveNodeSettings, self).set_auth(*args, **kwargs)

    def set_target_folder(self, folder, auth):
        """Configure this addon to point to a Google Drive folder

        :param str drive_folder_id:
        :param ExternalAccount external_account:
        :param User user:
        """
        self.drive_folder_id = folder['id']
        self.folder_path = folder['path']
        self.drive_folder_name = folder['name']


        # Tell the user's addon settings that this node is connecting
        self.user_settings.grant_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.drive_folder_id}
        )
        self.user_settings.save()

        # update this instance
        self.drive_folder_id = self.drive_folder_id
        self.save()

        self.owner.add_log(
            'googledrive_folder_selected',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder_id': self.drive_folder_id,
                'folder_name': self.drive_folder_name,
            },
            auth=auth,
        )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if not self.drive_folder_id:
            raise exceptions.AddonError('Folder is not configured')

        return {
            'folder': {
                'id': self.drive_folder_id,
                'name': self.drive_folder_name,
                'path': self.folder_path
            }
        }

    def create_waterbutler_log(self, auth, action, metadata):
        # cleaned_path = clean_path(metadata['path'])
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='googledrive')

        self.owner.add_log(
            'googledrive_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder_path,

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )
    @property
    def selected_folder_name(self):
        if self.drive_folder_id is None:
            return ''
        elif self.drive_folder_id == 'root':
            return 'Full Google Drive'
        else:
            # folder = self.folder_metadata(self.drive_folder_id)
            return self.drive_folder_name

    def folder_metadata(self, folder_id):
        """
        :param folder_id: Id of the selected folder
        :return: subfolders,if any.
        """
        client =GoogleDriveClient(self.external_account.oauth_key)
        folder = client.file_or_folder_metadata(fileId=folder_id)
        return folder

    def fetch_access_token(self):
        self.refresh_access_token()
        return self.external_account.oauth_key

    def refresh_access_token(self, force=False):
        if self._needs_refresh() or force:
            token = self.api._refresh_token(self.external_account.oauth_key, self.external_account.refresh_token)
            self.external_account.oauth_key = token['access_token']
            self.external_account.refresh_token = token['refresh_token']
            self.external_account.expires_at = datetime.utcfromtimestamp(token['expires_at'])
            self.save()

    def _needs_refresh(self):
        if self.external_account.expires_at is None:
            return False
        return (self.external_account.expires_at - datetime.utcnow()).total_seconds() < drive_settings.REFRESH_TIME

    def find_or_create_file_guid(self, path):
        path = os.path.join(self.folder_path, path.lstrip('/'))
        if self.folder_path != '/':
            path = '/' + path

        return GoogleDriveGuidFile.get_or_create(self.owner, path)