from website.addons.dmptool import model, routes

# MUST

SHORT_NAME = 'dmptool'
FULL_NAME = 'DMPTool'

ROUTES = [routes.api_routes]

MODELS = []

ADDED_DEFAULT = []
ADDED_MANDATORY = []

# make the dmptool addon show up as a widget like Zotero, Mendeley
VIEWS = ['widget']

# does this setting make it show up in the Files section?
HAS_HGRID_FILES = False

# SHOULD be one of documentation, storage, citations, security, bibliography, and other
# Additional categories can be added to ADDON_CATEGORIES in website.settings.defaults
# dmptool is the documentation category, according to https://cos.io/integrationgrants/ 

CATEGORIES = ['documentation']

# https://github.com/CenterForOpenScience/COSDev/blame/9cbf2db92fca22796c2c68593bd18bdcca97a0ed/docs/osf/addons.rst#L95
# Deprecated field, define as empty dict (``{}``)

INCLUDE_JS = {}
INCLUDE_CSS = {}

# I think the following are musts too
OWNERS = ['user', 'node']

# 'accounts' to have add-on show up in /settings/addons
# https://github.com/CenterForOpenScience/osf.io/blob/release/0.56.0/website/profile/views.py#L361
# 'node' presumably in the node addons setup (?)

CONFIGS = ['accounts', 'node']


MODELS = [
    model.DmptoolUserSettings,
    model.DmptoolNodeSettings
]

USER_SETTINGS_MODEL = model.DmptoolUserSettings
NODE_SETTINGS_MODEL = model.DmptoolNodeSettings
