import os

from addons.base.apps import BaseAddonAppConfig

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_node_settings.mako')

class DryadAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.dryad'
    label = 'addons_dryad'
    full_name = 'Dryad'
    short_name = 'dryad'
    owners = ['node']
    configs = ['node']
    categories = ['citations']
    has_hgrid_files = False
    max_file_size = 1000  # MB

    node_settings_template = NODE_SETTINGS_TEMPLATE
    user_settings_template = None

    DOI_SET = 'dryad_doi_set'
    DOI_UNSET = 'dryad_doi_unset'
    FILE_ADDED = 'dryad_file_added'
    FILE_REMOVED = 'dryad_file_removed'
    FILE_UPDATED = 'dryad_file_updated'
    FOLDER_CREATED = 'dryad_folder_created'
    FOLDER_SELECTED = 'dryad_folder_selected'
    NODE_AUTHORIZED = 'dryad_node_authorized'
    NODE_DEAUTHORIZED = 'dryad_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'dryad_node_deauthorized_no_user'

    actions = (DOI_SET, DOI_UNSET, FILE_ADDED, FILE_REMOVED, FILE_UPDATED, FOLDER_CREATED, FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, NODE_DEAUTHORIZED_NO_USER, )

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
