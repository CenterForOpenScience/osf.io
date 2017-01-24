from . import model

MODELS = [
    model.ZoteroUserSettings,
    model.ZoteroNodeSettings,
]


USER_SETTINGS_MODEL = model.ZoteroUserSettings
NODE_SETTINGS_MODEL = model.ZoteroNodeSettings
SHORT_NAME = 'zotero'
FULL_NAME = 'Zotero'

OWNERS = ['user', 'node']

CATEGORIES = ['citations']
