import os

from addons.base.apps import BaseAddonAppConfig

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(
    HERE,
    'templates',
    'forward_node_settings.mako',
)

class ForwardAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.forward'
    label = 'addons_forward'
    full_name = 'External Link'
    short_name = 'forward'
    configs = ['node']
    owners = ['node']
    views = ['widget']
    categories = ['other']
    node_settings_template = NODE_SETTINGS_TEMPLATE
    user_settings_template = None

    URL_CHANGED = 'forward_url_changed'

    actions = (URL_CHANGED, )

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
