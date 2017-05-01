import os

from addons.base.apps import BaseAddonAppConfig

HERE = os.path.dirname(os.path.abspath(__file__))

class TwoFactorAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.twofactor'
    label = 'addons_twofactor'
    full_name = 'Two-factor Authentication'
    short_name = 'twofactor'
    owners = ['user']
    configs = ['user']
    categories = ['security']
    added_mandatory = []
    widget_help = 'Two-Factor Authentication'

    user_settings_template = os.path.join(HERE, 'templates', 'twofactor_user_settings.mako')

    # FOLDER_SELECTED = 'dropbox_folder_selected'
    # NODE_AUTHORIZED = 'dropbox_node_authorized'
    # NODE_DEAUTHORIZED = 'dropbox_node_deauthorized'

    actions = tuple()
    # actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def routes(self):
        from .routes import settings_routes
        return [settings_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')
