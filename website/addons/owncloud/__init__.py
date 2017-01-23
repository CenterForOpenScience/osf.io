from website.addons.owncloud import model

MODELS = [
    model.AddonOwnCloudUserSettings,
    model.AddonOwnCloudNodeSettings,
]
USER_SETTINGS_MODEL = model.AddonOwnCloudUserSettings
NODE_SETTINGS_MODEL = model.AddonOwnCloudNodeSettings
SHORT_NAME = 'owncloud'
FULL_NAME = 'ownCloud'
OWNERS = ['user', 'node']
CATEGORIES = ['storage']
