from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.dropboxbusiness.settings import MAX_UPLOAD_SIZE
from website.util import rubeus


def dropboxbusiness_root(addon_config, node_settings, auth, **kwargs):
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name='',
        permissions=auth,
        user=auth.user,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]


class DropboxBusinessAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.dropboxbusiness'
    label = 'addons_dropboxbusiness'
    full_name = 'Dropbox Business'
    short_name = 'dropboxbusiness'
    configs = ['accounts', 'node']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE
    owners = ['user', 'node']
    categories = ['storage']

    get_hgrid_data = dropboxbusiness_root

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
