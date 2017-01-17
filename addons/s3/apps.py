import os
from addons.base.apps import BaseAddonAppConfig

from addons.s3.views import s3_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class S3AddonAppConfig(BaseAddonAppConfig):

    name = 'addons.s3'
    label = 'addons_s3'
    full_name = 'Amazon S3'
    short_name = 's3'
    configs = ['accounts', 'node']
    has_hgrid_files = True
    max_file_size = 128  # MB
    node_settings_template = os.path.join(TEMPLATE_PATH, 's3_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 's3_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return s3_root_folder

    BUCKET_LINKED = 's3_bucket_linked'
    BUCKET_UNLINKED = 's3_bucket_unlinked'
    FILE_ADDED = 's3_file_added'
    FILE_REMOVED = 's3_file_removed'
    FILE_UPDATED = 's3_file_updated'
    FOLDER_CREATED = 's3_folder_created'
    NODE_AUTHORIZED = 's3_node_authorized'
    NODE_DEAUTHORIZED = 's3_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 's3_node_deauthorized_no_user'

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
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
