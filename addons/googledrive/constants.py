from addons.googledrive import routes, views

ROUTES = [routes.api_routes]

SHORT_NAME = 'googledrive'
FULL_NAME = 'Google Drive'

OWNERS = ['user', 'node']  # can include any of ['user', 'node']

VIEWS = []  # page, widget
CONFIGS = ['accounts', 'node']  # any of ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'page': [],
    'files': []
}

INCLUDE_CSS = {
    'page': [],
    'files': []
}

HAS_HGRID_FILES = True  # set to True for storage addons that display in HGrid
GET_HGRID_DATA = views.googledrive_root_folder
# MAX_FILE_SIZE = 10  # MB

NODE_SETTINGS_TEMPLATE = None  # use default nodes settings templates
USER_SETTINGS_TEMPLATE = None  # use default user settings templates
