from addons.base.apps import BaseAddonAppConfig


class TwoFactorAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.twofactor'
    label = 'addons_twofactor'
    full_name = 'Two-factor Authentication'
    short_name = 'twofactor'
    configs = ['user']
    added_mandatory = []

    # FOLDER_SELECTED = 'dropbox_folder_selected'
    # NODE_AUTHORIZED = 'dropbox_node_authorized'
    # NODE_DEAUTHORIZED = 'dropbox_node_deauthorized'

    actions = tuple()
    # actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('UserSettings')
