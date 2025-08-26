from addons.base.apps import BaseAddonAppConfig


class AzureBlobStorageAddonAppConfig(BaseAddonAppConfig):

    default = True
    name = 'addons.azureblobstorage'
    label = 'addons_azureblobstorage'
    full_name = 'Azure Blob Storage'
    short_name = 'azureblobstorage'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True

    # Define actions for NodeLog
    FOLDER_SELECTED = 'azureblobstorage_folder_selected'
    NODE_AUTHORIZED = 'azureblobstorage_node_authorized'
    NODE_DEAUTHORIZED = 'azureblobstorage_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def routes(self):
        # No Flask routes needed for gravyvalet-managed addon
        return []

    @property
    def user_settings(self):
        # No UserSettings for gravyvalet-managed addon
        return None

    @property
    def node_settings(self):
        # No NodeSettings for gravyvalet-managed addon
        return None
