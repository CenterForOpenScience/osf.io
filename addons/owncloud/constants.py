import os

from addons.owncloud.routes import api_routes
from addons.owncloud import views

ROUTES = [api_routes]

ADDED_DEFAULT = []
ADDED_MANDATORY = []

SHORT_NAME = 'owncloud'
FULL_NAME = 'ownCloud'
OWNERS = ['user', 'node']
VIEWS = []
CONFIGS = ['accounts', 'node']
CATEGORIES = ['storage']
HAS_HGRID_FILES = True
GET_HGRID_DATA = views.owncloud_root_folder
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'owncloud_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'owncloud_user_settings.mako')
