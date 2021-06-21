# OAuth app keys
ONEDRIVE_KEY = None
ONEDRIVE_SECRET = None

ONEDRIVE_OAUTH_TOKEN_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
ONEDRIVE_OAUTH_AUTH_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'

REFRESH_TIME = 30 * 60  # 30 minutes

DEFAULT_ROOT_ID = 'root'  # id string to identify the root folder

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 5 * 1024  # 5 GB

TEAM_FOLDER_NAME_FORMAT = '{title}_GRDM_{guid}'  # available: {title} {guid}
TEAM_MEMBER_LIST_FILENAME = 'users.xlsx'
TEAM_MEMBER_LIST_SHEETNAME = 'Users'

TEAM_MEMBER_LIST_CACHE_TIMEOUT = 60
TEAM_MEMBER_USER_CACHE_TIMEOUT = 60
