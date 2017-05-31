CLIENT_ID = None
CLIENT_SECRET = None

API_BASE_URL = 'https://api.figshare.com/v2/'

MAX_RENDER_SIZE = 1000

FIGSHARE_OAUTH_TOKEN_ENDPOINT = '{}{}'.format(API_BASE_URL, 'token')
FIGSHARE_OAUTH_AUTH_ENDPOINT = 'https://figshare.com/account/applications/authorize'

FIGSHARE_DEFINED_TYPE_NUM_MAP = {
    'figure': 1,
    'media': 2,
    'dataset': 3,
    'fileset': 4,
    'poster': 5,
    'paper': 6,
    'presentation': 7,
    'thesis': 8,
    'code': 9,
}
