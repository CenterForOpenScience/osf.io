from .model.settings import AddonBitbucketSettings
from .routes import settings_routes, page_routes

SETTINGS_MODEL = AddonBitbucketSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'bitbucket'
FULL_NAME = 'Bitbucket'

ADDED_BY_DEFAULT = False

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'Bitbucket Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'Bitbucket Addon Settings',
            'contents': [
                {
                    'id': 'bitbucket_user',
                    'type': 'textfield',
                    'label': 'Bitbucket User',
                    'required': True,
                },
                {
                    'id': 'bitbucket_repo',
                    'type': 'textfield',
                    'label': 'Bitbucket Repo',
                    'required': True,
                },
                {
                    'id': 'bitbucket_code',
                    'type': 'htmlfield',
                    'label': 'Bitbucket Access',
                    'content': '''
                        <div>
                            <a id="bitbucketAddKey" class="btn btn-primary" style="display: none;">Get Access Token</a>
                            <a id="bitbucketDelKey" class="btn btn-danger" style="display: none;">Delete Access Token</a>
                            <span id="bitbucketKeyUser" style="margin-left: 10px;"></span>
                        </div>
                    ''',
                },
                {
                    'id': 'bitbucket_oauth_user',
                    'type': 'hiddenfield',
                    'label': '',
                }
            ]
        }
    ]
}
