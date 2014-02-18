from .model import AddonTwitterNodeSettings
#AddonGitHubUserSettings,
from .routes import settings_routes, page_routes
#
#USER_SETTINGS_MODEL = AddonGitHubUserSettings
NODE_SETTINGS_MODEL = AddonTwitterNodeSettings



#
ROUTES = [settings_routes, page_routes]
#
SHORT_NAME = 'twitter'
FULL_NAME = 'Twitter'
OWNERS = ['node']

#
#OWNERS = ['user', 'node']
#
ADDED_TO = {
    'user': False,
    'node': False,
}
#
VIEWS = ['widget', 'page']
CONFIGS = ['user', 'node']
#
CATEGORIES = ['feed']
#
#INCLUDE_JS = {
#    'widget': ['jquery.githubRepoWidget.js'],
#    'page': [
#        '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
#        '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
#        '/static/vendor/dropzone/dropzone.js',
#        '/static/js/slickgrid.custom.min.js',
#        '/static/js/hgrid.js',
#        'hgrid-github.js',
#    ],
#}
#
#INCLUDE_CSS = {
#    'widget': [],
#    'page': ['/static/css/hgrid-base.css'],
#}
#
WIDGET_HELP = 'Twitter Add-on Alpha'
