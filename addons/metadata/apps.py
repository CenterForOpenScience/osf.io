# -*- coding: utf-8 -*-
import os
from addons.base.apps import BaseAddonAppConfig
from . import DISPLAY_NAME, SHORT_NAME


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class AddonAppConfig(BaseAddonAppConfig):

    short_name = SHORT_NAME
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)

    full_name = DISPLAY_NAME

    owners = ['user', 'node']

    views = ['page']
    configs = ['node']

    categories = ['other']

    include_js = {}

    include_css = {
        'widget': [],
        'page': [],
    }

    has_page_icon = False

    node_settings_template = os.path.join(TEMPLATE_PATH, 'metadata_node_settings.mako')

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes, routes.page_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
