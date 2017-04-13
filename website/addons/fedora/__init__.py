from website.addons.fedora import model
from website.addons.fedora.routes import api_routes
from website.addons.fedora import views

import os

MODELS = [
    model.AddonFedoraUserSettings,
    model.AddonFedoraNodeSettings,
]
USER_SETTINGS_MODEL = model.AddonFedoraUserSettings
NODE_SETTINGS_MODEL = model.AddonFedoraNodeSettings
ROUTES = [api_routes]

ADDED_DEFAULT = []
ADDED_MANDATORY = []

SHORT_NAME = 'fedora'
FULL_NAME = 'Fedora'
OWNERS = ['user', 'node']
VIEWS = []
CONFIGS = ['accounts', 'node']
CATEGORIES = ['storage']
HAS_HGRID_FILES = True
GET_HGRID_DATA = views.fedora_root_folder
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'fedora_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'fedora_user_settings.mako')
