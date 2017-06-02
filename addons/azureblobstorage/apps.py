import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder

azureblobstorage_root_folder = generic_root_folder('azureblobstorage')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class AzureBlobStorageAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.azureblobstorage'
    label = 'addons_azureblobstorage'
    full_name = 'Azure Blob Storage'
    short_name = 'azureblobstorage'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = 128  # MB
    node_settings_template = os.path.join(TEMPLATE_PATH, 'azureblobstorage_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'azureblobstorage_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return azureblobstorage_root_folder

    BUCKET_LINKED = 'azureblobstorage_bucket_linked'
    BUCKET_UNLINKED = 'azureblobstorage_bucket_unlinked'
    FILE_ADDED = 'azureblobstorage_file_added'
    FILE_REMOVED = 'azureblobstorage_file_removed'
    FILE_UPDATED = 'azureblobstorage_file_updated'
    FOLDER_CREATED = 'azureblobstorage_folder_created'
    NODE_AUTHORIZED = 'azureblobstorage_node_authorized'
    NODE_DEAUTHORIZED = 'azureblobstorage_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'azureblobstorage_node_deauthorized_no_user'

    actions = (BUCKET_LINKED,
        BUCKET_UNLINKED,
        FILE_ADDED,
        FILE_REMOVED,
        FILE_UPDATED,
        FOLDER_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER)

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
