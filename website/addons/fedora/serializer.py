from website.util import api_url_for
from website.addons.base.serializer import AddonSerializer

class FedoraSerializer(AddonSerializer):

    @property
    def addon_short_name(self):
        return 'fedora'

    @property
    def user_is_owner(self):
        return True

    @property
    def credentials_owner(self):
        return True

    @property
    def serialized_urls(self):
        ret = self.addon_serialized_urls
        ret.update({'settings': web_url_for('user_addons')})
        return ret

    def serialize_settings(self, node_settings, current_user, client=None):
        result = {
            'userIsOwner': True,
            'nodeHasAuth': True,
            'urls': self.serialized_urls,
            'validCredentials': True,
            'userHasAuth': True,
            'folder': {'name': '/', 'path': '/'},
        }

        return result
        
    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'importAuth': node.api_url_for('fedora_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('fedora_folder_list'),
            'config': node.api_url_for('fedora_set_config'),
            'deauthorize': node.api_url_for('fedora_deauthorize_node'),
            'accounts': node.api_url_for('fedora_account_list'),
        }
