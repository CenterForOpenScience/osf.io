# Drive credentials
CLIENT_ID = 'chaneme'
CLIENT_SECRET = 'changeme'

#https://developers.google.com/identity/protocols/OAuth2#expiration
EXPIRY_TIME = 60 * 60 * 24 * 175  # 175 days
REFRESH_TIME = 5 * 60  # 5 minutes


# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive',
]
OAUTH_BASE_URL = 'https://accounts.google.com/o/oauth2/'
API_BASE_URL = 'https://www.googleapis.com/'

FLOWABLE_HOST = 'http://localhost:9977/flowable-rest/'
FLOWABLE_RESEARCH_APP_ID = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
FLOWABLE_USER = 'testuser'
FLOWABLE_PASSWORD = 'testpass'
