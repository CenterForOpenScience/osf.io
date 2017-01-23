from website.addons.github import model

MODELS = [
    model.GitHubUserSettings,
    model.GitHubNodeSettings,
]
USER_SETTINGS_MODEL = model.GitHubUserSettings
NODE_SETTINGS_MODEL = model.GitHubNodeSettings
SHORT_NAME = 'github'
FULL_NAME = 'GitHub'
OWNERS = ['user', 'node']
CATEGORIES = ['storage']
