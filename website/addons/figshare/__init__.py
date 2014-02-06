from .model import AddonFigShareNodeSettings, AddonFigShareUserSettings
from .routes import settings_routes, page_routes

USER_SETTINGS_MODEL = AddonFigShareUserSettings
NODE_SETTINGS_MODEL = AddonFigShareNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'figshare'
FULL_NAME = 'FigShare'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget', 'page']
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
