from website.addons.base.serializer import StorageAddonSerializer
from website.addons.fedora.settings import DEFAULT_HOSTS
from website.util import web_url_for


class FedoraSerializer(StorageAddonSerializer):

    addon_short_name = 'fedora'

    def serialized_folder(self, node_settings):
        return {
            'name': node_settings.fetch_folder_name(),
            'path': node_settings.folder_id
        }

    def credentials_are_valid(self, user_settings, client=None):
        return True

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'auth': node.api_url_for('fedora_add_user_account'),
            'accounts': node.api_url_for('fedora_account_list'),
            'importAuth': node.api_url_for('fedora_import_auth'),
            'deauthorize': node.api_url_for('fedora_deauthorize_node'),
            'folders': node.api_url_for('fedora_folder_list'),
            'files': node.web_url_for('collect_file_trees'),
            'config': node.api_url_for('fedora_set_config'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result

    @property
    def serialized_node_settings(self):
        result = super(FedoraSerializer, self).serialized_node_settings
        result['hosts'] = DEFAULT_HOSTS
        return result

    @property
    def serialized_user_settings(self):
        result = super(FedoraSerializer, self).serialized_user_settings
        result['hosts'] = DEFAULT_HOSTS
        return result

    def serialize_settings(self, node_settings, current_user, client=None):
        ret = super(FedoraSerializer, self).serialize_settings(node_settings, current_user, client)
        ret['hosts'] = DEFAULT_HOSTS
        return ret
