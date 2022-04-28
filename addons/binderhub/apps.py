# -*- coding: utf-8 -*-
import os
from addons.base.apps import BaseAddonAppConfig
from . import SHORT_NAME, FULL_NAME


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class AddonAppConfig(BaseAddonAppConfig):

    short_name = SHORT_NAME
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)

    full_name = FULL_NAME

    owners = ['user', 'node']

    views = [
        'page'
    ]

    configs = ['accounts', 'node']

    categories = ['other']
    has_page_icon = False

    node_settings_template = os.path.join(TEMPLATE_PATH, 'binderhub_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'binderhub_user_settings.mako')

    @property
    def routes(self):
        from . import routes
        return [
            routes.page_routes,
            routes.api_routes
        ]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
