import os

from addons.base.apps import BaseAddonAppConfig

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class DataverseAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.dataverse'
    label = 'addons_dataverse'
    full_name = 'Dataverse'
    short_name = 'dataverse'
    configs = ['accounts', 'node']
    views = ['widget']
    has_hgrid_files = True
    node_settings_template = os.path.join(TEMPLATE_PATH, 'dataverse_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'dataverse_user_settings.mako')

    @property
    def get_hgrid_data(self):
        # Avoid circular import
        from addons.dataverse.views import _dataverse_root_folder
        return _dataverse_root_folder

    FILE_ADDED = 'dataverse_file_added'
    FILE_REMOVED = 'dataverse_file_removed'
    DATASET_LINKED = 'dataverse_dataset_linked'
    DATASET_PUBLISHED = 'dataverse_dataset_published'
    STUDY_LINKED = 'dataverse_study_linked'
    STUDY_RELEASED = 'dataverse_study_released'
    NODE_AUTHORIZED = 'dataverse_node_authorized'
    NODE_DEAUTHORIZED = 'dataverse_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'dataverse_node_deauthorized_no_user'

    actions = (FILE_ADDED, FILE_REMOVED, DATASET_LINKED, DATASET_PUBLISHED, STUDY_LINKED, STUDY_RELEASED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, NODE_DEAUTHORIZED_NO_USER)

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
