from addons.base.apps import BaseAddonConfig


class BoxAddonConfig(BaseAddonConfig):

    name = 'addons.box'
    label = 'addons_box'
    full_name = 'Box'

    FOLDER_SELECTED = 'box_folder_selected'
    NODE_AUTHORIZED = 'box_node_authorized'
    NODE_DEAUTHORIZED = 'box_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
