from addons.base.apps import BaseAddonConfig
# from addons.dropbox.models import DropboxUserSettings
# from addons.dropbox.models import DropboxNodeSettings


class DropboxAddonConfig(BaseAddonConfig):

    name = 'addons.dropbox'
    full_name = 'DropBox'

    FOLDER_SELECTED = 'dropbox_folder_selected'
    NODE_AUTHORIZED = 'dropbox_node_authorized'
    NODE_DEAUTHORIZED = 'dropbox_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('DropboxUserSettings')

    @property
    def node_settings(self):
        return self.get_model('DropboxNodeSettings')
