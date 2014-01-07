from .model.settings import AddonS3Settings
from .routes import settings_routes

SETTINGS_MODEL = AddonS3Settings

ROUTES = [settings_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'

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

WIDGET_HELP = 'AWS S3 Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'S3 Addon Settings',
            'contents': [
                {
                    'id': 'access_key',
                    'type': 'textfield',
                    'label': 'S3 Access Key',
                    'required': True,
                },
                {
                    'id': 'secret_key',
                    'type': 'textfield',
                    'label': 'S3 Secret Key',
                    'required': True,
                }
            ]
        }
    ]
}