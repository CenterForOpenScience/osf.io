from .model.settings import AddonZoteroNodeSettings
from .routes import settings_routes, page_routes, widget_routes

SETTINGS_MODEL = AddonZoteroNodeSettings

ROUTES = [settings_routes, page_routes, widget_routes]

SHORT_NAME = 'zotero'
FULL_NAME = 'Zotero'

ADDED_BY_DEFAULT = False

CATEGORIES = ['bibliography']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

WIDGET_HELP = 'Zotero Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'Zotero Addon Settings',
            'contents': [
                {
                    'id': 'zotero_id',
                    'type': 'textfield',
                    'label': 'Zotero Group ID',
                    'required': True,
                },
            ]
        }
    ]
}
