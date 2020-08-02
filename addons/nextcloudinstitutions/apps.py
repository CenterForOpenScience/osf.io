import os

from addons.base.apps import BaseAddonAppConfig
from website.util import rubeus

FULL_NAME = 'Nextcloud for Institutions'
SHORT_NAME = 'nextcloudinstitutions'
LONG_NAME = 'addons.{}'.format(SHORT_NAME)

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


def nextcloudinstitutions_root(addon_config, node_settings, auth, **kwargs):
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


class NextcloudInstitutionsAddonAppConfig(BaseAddonAppConfig):
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)
    full_name = FULL_NAME
    short_name = SHORT_NAME
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True

    user_settings_template = os.path.join(
        TEMPLATE_PATH, 'nextcloudinstitutions_user_settings.mako')
    # node_settings_template is not used.

    get_hgrid_data = nextcloudinstitutions_root

    actions = ()

    # default value for RdmAddonOption.is_allowed for GRDM Admin
    is_allowed_default = False
    for_institutions = True

    @property
    def routes(self):
        from .routes import api_routes
        return [api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
