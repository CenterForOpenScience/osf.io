from addons.base.apps import BaseAddonConfig


class OSFStorageAddonConfig(BaseAddonConfig):

    name = 'addons.osfstorage'
    label = 'addons_osfstorage'
    full_name = 'OSFStorage'

    FOLDER_SELECTED = 'osfstorage_folder_selected'
    NODE_AUTHORIZED = 'osfstorage_node_authorized'
    NODE_DEAUTHORIZED = 'osfstorage_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
