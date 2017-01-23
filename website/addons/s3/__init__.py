from . import model

MODELS = [model.S3UserSettings, model.S3NodeSettings]
USER_SETTINGS_MODEL = model.S3UserSettings
NODE_SETTINGS_MODEL = model.S3NodeSettings

SHORT_NAME = 's3'
FULL_NAME = 'Amazon S3'


OWNERS = ['user', 'node']
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']
