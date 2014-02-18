from . import routes, views, model

MODELS = [model.AddonFigShareUserSettings, model.AddonFigShareNodeSettings] 
USER_SETTINGS_MODEL = model.AddonFigShareUserSettings
NODE_SETTINGS_MODEL = model.AddonFigShareNodeSettings

ROUTES = [routes.settings_routes, routes.page_routes, routes.api_routes]

SHORT_NAME = 'figshare'
FULL_NAME = 'FigShare'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget']
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': ['/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
             '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
             '/static/vendor/dropzone/dropzone.js',
             '/static/js/slickgrid.custom.min.js',
             #'/static/js/hgrid.js',            
             'hgrid.min.js',
             'figshare_page.js'
             ],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'FigShare Add-on Alpha'

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.figshare_hgrid_data

MAX_FILE_SIZE = 1024*1024
