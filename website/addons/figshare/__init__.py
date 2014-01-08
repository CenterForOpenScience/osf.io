from .model.settings import AddonFigShareNodeSettings
from .routes import settings_routes

SETTINGS_MODEL = AddonFigShareNodeSettings

ROUTES = [settings_routes]

SHORT_NAME = 'figshare'
FULL_NAME = 'FigShare'

ADDED_BY_DEFAULT = False

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

WIDGET_HELP = 'FigShare Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'FigShare Addon Settings',
            'contents': [
                {
                    'id': 'figshare_id',
                    'type': 'textfield',
                    'label': 'FigShare Project ID',
                    'required': True,
                },
            ]
        }
    ]
}
