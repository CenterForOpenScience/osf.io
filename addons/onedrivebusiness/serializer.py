from oauthlib.oauth2 import InvalidGrantError
from addons.base.serializer import StorageAddonSerializer
from addons.onedrivebusiness import SHORT_NAME
from website.util import web_url_for


class OneDriveBusinessSerializer(StorageAddonSerializer):
    addon_short_name = SHORT_NAME

    REQUIRED_URLS = []

    def credentials_are_valid(self, user_settings, client):
        try:
            self.node_settings.fetch_access_token()
        except (InvalidGrantError, AttributeError):
            return False
        return True

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('{}_account_list'.format(SHORT_NAME)),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                                          uid=user_settings.owner._id)
        return result

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }
