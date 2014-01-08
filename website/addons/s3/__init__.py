from .model.settings import AddonS3UserSettings,AddonS3NodeSettings
from .routes import settings_routes

USER_MODEL = AddonS3UserSettings
SETTINGS_MODEL = AddonS3NodeSettings

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
                },
                {
                    'id': 'bucket_name',
                    'type': 'textfield',
                    'label': 'S3 Bucket Name',
                    'required': True,
                }
            ]
        }
    ]
}