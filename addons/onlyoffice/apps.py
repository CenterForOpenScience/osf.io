# -*- coding: utf-8 -*-
import os
from addons.base.apps import BaseAddonAppConfig
from . import SHORT_NAME

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class AddonAppConfig(BaseAddonAppConfig):

    short_name = SHORT_NAME
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)

    full_name = 'ONLYOFFICE'

    owners = ['node']

    views = []
    configs = ['node']

    categories = ['other']

    include_js = {}

    include_css = {}

    node_settings_template = os.path.join(TEMPLATE_PATH, 'node_settings.mako')

    @property
    def routes(self):
        from . import routes
        #return [routes.api_routes, routes.edit_routes, routes.wopi_routes]
        return [routes.edit_routes, routes.wopi_routes]

    #@property
    #def user_settings(self):
    #    return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
