import os
from addons.base.apps import BaseAddonAppConfig


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class JupyterhubAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.jupyterhub'
    label = 'addons_jupyterhub'

    short_name = 'jupyterhub'
    full_name = 'JupyterHub'

    owners = ['node']

    views = ['widget']
    configs = ['node']

    categories = ['other']

    include_js = {
        'widget': []
    }

    include_css = {
        'widget': []
    }

    node_settings_template = os.path.join(TEMPLATE_PATH, 'jupyterhub_node_settings.mako')

    @property
    def routes(self):
        from addons.jupyterhub import routes
        return [routes.widget_routes, routes.api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
