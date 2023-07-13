import os

from addons.base.apps import BaseAddonAppConfig
from addons.dropboxbusiness.settings import MAX_UPLOAD_SIZE
from website.util import rubeus

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

def dropboxbusiness_root(addon_config, node_settings, auth, **kwargs):
    from addons.osfstorage.models import Region
    # GRDM-37149: Hide deactivated institutional storage
    if not node_settings.complete:
        return None
    node = node_settings.owner
    institution = node_settings.fileaccess_option.institution
    if Region.objects.filter(_id=institution._id).exists():
        region = Region.objects.get(_id=institution._id)
        if region:
            node_settings.region = region
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

    user_settings_template = os.path.join(TEMPLATE_PATH, 'dropboxbusiness_user_settings.mako')
    # node_settings_template is not used.

    get_hgrid_data = dropboxbusiness_root

    # default value for RdmAddonOption.is_allowed for GRDM Admin
    is_allowed_default = False
    for_institutions = True

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')

    @property
    def routes(self):
        from . import routes
        return [routes.auth_routes, routes.api_routes]
