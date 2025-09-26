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

    added_default = ['node']

    has_page_icon = False

    node_settings_template = os.path.join(TEMPLATE_PATH, 'metadata_node_settings.mako')

    excel_file_maximum_size = 10485760
    text_file_maximum_size = 10485760
    image_file_maximum_size = 10485760
    any_file_maximum_size = 10485760

    text_file_extension = ['txt', 'csv', 'tsv']
    excel_file_extension = ['xlsx', 'xls']
    image_file_extension = ['jpg', 'jpeg', 'tif', 'png', 'bmp']

    delimiters = {'\t': 'tab', ';': 'semicolon', ',': 'comma', ' ': 'space'}
    delimiter_counts = {'\t': 0, ';': 0, ',': 0, ' ': 0}

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
