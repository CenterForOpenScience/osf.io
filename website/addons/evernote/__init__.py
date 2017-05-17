from website.addons.evernote import model, routes, views

# MUST

SHORT_NAME = 'evernote'
FULL_NAME = 'Evernote'

ROUTES = [routes.api_routes]

ADDED_DEFAULT = []
ADDED_MANDATORY = []

# make the evernote addon show up as a widget like Zotero, Mendeley
VIEWS = ['widget']

# does this setting make it show up in the Files section?
HAS_HGRID_FILES = True
GET_HGRID_DATA = views.evernote_root_folder

# SHOULD be one of documentation, storage, citations, security, bibliography, and other
# Additional categories can be added to ADDON_CATEGORIES in website.settings.defaults
# evernote is the documentation category, according to https://cos.io/integrationgrants/ (https://www.evernote.com/l/AAG7vFn4MqFHd7g6tDChuwk2DKPWhp0oNCM)

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
    model.EvernoteUserSettings,
    model.EvernoteNodeSettings
]

USER_SETTINGS_MODEL = model.EvernoteUserSettings
NODE_SETTINGS_MODEL = model.EvernoteNodeSettings
