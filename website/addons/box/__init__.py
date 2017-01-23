from website.addons.box import model


MODELS = [
    model.BoxUserSettings,
    model.BoxNodeSettings,
]

USER_SETTINGS_MODEL = model.BoxUserSettings
NODE_SETTINGS_MODEL = model.BoxNodeSettings

SHORT_NAME = 'box'
FULL_NAME = 'Box'

OWNERS = ['user', 'node']
CATEGORIES = ['storage']
