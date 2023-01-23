# OAuth app keys
ONEDRIVE_KEY = None
ONEDRIVE_SECRET = None

MSGRAPH_API_URL = 'https://graph.microsoft.com/v1.0'

REFRESH_TIME = 30 * 60  # 30 minutes

DEFAULT_ROOT_ID = 'root'  # id string to identify the root folder

ONEDRIVE_AUTHORITY_BASE = 'https://login.microsoftonline.com/'
ONEDRIVE_DEFAULT_TENANT = 'common'
ONEDRIVE_DEFAULT_AUTHORITY = ONEDRIVE_AUTHORITY_BASE + ONEDRIVE_DEFAULT_TENANT
ONEDRIVE_DEFAULT_OAUTH_TOKEN_ENDPOINT = ONEDRIVE_DEFAULT_AUTHORITY + '/oauth2/v2.0/token?'
ONEDRIVE_DEFAULT_OAUTH_AUTH_ENDPOINT = ONEDRIVE_DEFAULT_AUTHORITY + '/oauth2/v2.0/authorize?'
ONEDRIVE_DEFAULT_SCOPES = ['User.Read offline_access Files.Read Files.Read.All Files.ReadWrite']
