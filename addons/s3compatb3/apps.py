import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.s3compatb3.settings import MAX_UPLOAD_SIZE

s3compatb3_root_folder = generic_root_folder('s3compatb3')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class S3CompatB3AddonAppConfig(BaseAddonAppConfig):

    name = 'addons.s3compatb3'
    label = 'addons_s3compatb3'
    full_name = 'Oracle Cloud Infrastructure Object Storage'
    short_name = 's3compatb3'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE
    node_settings_template = os.path.join(TEMPLATE_PATH, 's3compatb3_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 's3compatb3_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return s3compatb3_root_folder

    BUCKET_LINKED = 's3compatb3_bucket_linked'
    BUCKET_UNLINKED = 's3compatb3_bucket_unlinked'
    FILE_ADDED = 's3compatb3_file_added'
    FILE_REMOVED = 's3compatb3_file_removed'
    FILE_UPDATED = 's3compatb3_file_updated'
    FOLDER_CREATED = 's3compatb3_folder_created'
    NODE_AUTHORIZED = 's3compatb3_node_authorized'
    NODE_DEAUTHORIZED = 's3compatb3_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 's3compatb3_node_deauthorized_no_user'

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
