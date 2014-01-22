from . import routes, views, model

MODELS = [model.AddonOsfFilesNodeSettings, model.NodeFile]
NODE_SETTINGS_MODEL = model.AddonOsfFilesNodeSettings

ROUTES = [
    routes.settings_routes,
    routes.widget_routes,
    routes.web_routes,
    routes.api_routes
]

SHORT_NAME = 'osffiles'
FULL_NAME = 'OSF Files'

OWNERS = ['node']

ADDED_TO = {
    'node': True,
}

VIEWS = []
CONFIGS = []

CATEGORIES = ['storage']

GET_HGRID_DATA = views.get_osffiles
GET_HGRID_DUMMY = views.osffiles_dummy_folder
