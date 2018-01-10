from website.util import api_url_for
from addons.base.serializer import StorageAddonSerializer
from rackspace import connection
import openstack


class CloudFilesSerializer(StorageAddonSerializer):

    addon_short_name = 'cloudfiles'

    def credentials_are_valid(self, user_settings, client=None):
        node = self.node_settings

        if node.external_account:
            external_account = node.external_account
        else:
            return False

        try:
            # Region is required for the client, but arbitrary here.
            conn = connection.Connection(username=external_account.provider_id,
                                         api_key=external_account.oauth_secret,
                                         region=node.folder_region)
            for _ in conn.object_store.containers():  # Checks if has necessary permission
                pass
            return True
        except openstack.exceptions.SDKException:
            return False

    def serialized_folder(self, node_settings):
        path = node_settings.folder_name
        return {
            'name': path if path != '/' else '/ (Full Rackspace Cloud Files)',
            'path': path
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect', service_name='cloudfiles'),
            'createContainer': node.api_url_for('cloudfiles_create_container'),
            'importAuth': node.api_url_for('cloudfiles_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('cloudfiles_folder_list'),
            'config': node.api_url_for('cloudfiles_set_config'),
            'deauthorize': node.api_url_for('cloudfiles_deauthorize_node'),
            'accounts': node.api_url_for('cloudfiles_account_list'),
        }
