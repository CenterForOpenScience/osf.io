#from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.base.serializer import StorageAddonSerializer

from website.util import api_url_for
from website.addons.evernote import utils

from evernote.edam.error.ttypes import EDAMUserException

class EvernoteSerializer(StorageAddonSerializer):

    addon_short_name = 'evernote'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            try:
                client = client or utils.get_evernote_client(token=user_settings.external_accounts[0].oauth_key)
            except EDAMUserException:
                return False
        return True

    def serialized_folder(self, node_settings):
        path = node_settings.fetch_full_folder_path()
        return {
            'path': path,
            'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full Evernote)'
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='evernote'),
            'importAuth': node.api_url_for('evernote_add_user_auth'),
            'folders': node.api_url_for('evernote_folder_list'),
            'config': node.api_url_for('evernote_set_config'),
            'notes': node.api_url_for('evernote_notes'),
            'note': node.api_url_for('evernote_note'),
            # TO DO files -- fix what 'files' should be
            # https://github.com/CenterForOpenScience/osf.io/pull/4670/#discussion_r67703341
            'files': node.api_url_for('evernote_notes'),
            'deauthorize': node.api_url_for('evernote_deauthorize_node'),
            'accounts': node.api_url_for('evernote_get_user_settings'),
        }
