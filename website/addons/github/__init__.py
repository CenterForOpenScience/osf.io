from .model.settings import AddonGitHubUserSettings, AddonGitHubNodeSettings
from .routes import settings_routes, page_routes

USER_MODEL = AddonGitHubUserSettings
SETTINGS_MODEL = AddonGitHubNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

ADDED_BY_DEFAULT = False

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': ['jquery.githubRepoWidget.js'],
    'page': [
        '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
        '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
        '/static/vendor/dropzone/dropzone.js',
        '/static/js/slickgrid.custom.min.js',
        '/static/js/hgrid.js',
        'hgrid-github.js',
    ],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'GitHub Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'GitHub Addon Settings',
            'contents': [
                {
                    'id': 'github_user',
                    'type': 'textfield',
                    'label': 'GitHub User',
                    'required': True,
                },
                {
                    'id': 'github_repo',
                    'type': 'textfield',
                    'label': 'GitHub Repo',
                    'required': True,
                },
                {
                    'id': 'github_has_authentication',
                    'type': 'htmlfield',
                    'label': 'GitHub Access',
                    'content': '''
                        <div>
                            <a id="githubAddKey" class="btn btn-primary" style="display: none;"></a>
                            <a id="githubDelKey" class="btn btn-danger" style="display: none;">Delete Access Token</a>
                            <span id="githubKeyUser" style="margin-left: 10px;"></span>
                        </div>
                    ''',
                },
                {
                    'id': 'github_has_user_authentication',
                    'type': 'hiddenfield',
                    'label': '',
                },
                {
                    'id': 'github_authenticated_user',
                    'type': 'hiddenfield',
                    'label': '',
                }
            ]
        }
    ]
}
