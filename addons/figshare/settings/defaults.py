CLIENT_ID = None
CLIENT_SECRET = None

API_BASE_URL = 'https://api.figshare.com/v2/'

MAX_RENDER_SIZE = 1000

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 50

FIGSHARE_OAUTH_TOKEN_ENDPOINT = '{}{}'.format(API_BASE_URL, 'token')
FIGSHARE_OAUTH_AUTH_ENDPOINT = 'https://figshare.com/account/applications/authorize'

# Each figshare article has a type integer that corresponds to an article type.
FIGSHARE_IDS_TO_TYPES = {
    1: 'figure',
    2: 'media',
    3: 'dataset',
    4: 'fileset',  # Unofficially deprecated and replaced by type 3 dataset
    5: 'poster',
    6: 'journal contribution',
    7: 'presentation',
    8: 'thesis',
    9: 'software',
    # For unknown reasons, 10 does not exist
    11: 'online resource',
    12: 'preprints',
    13: 'book',
    14: 'conference',
}

# When this addon was originally implemented, only type 4 ("fileset") articles behaved like folders
# and contained multiple files.  Since then, figshare has changed their API so that type 3 articles
# ("datasets") are the default multiple-file containers.  New requests to create "fileset"s are
# automatically converted to create "dataset"s.  Pre-exisiting "fileset"s retain the same id.  To
# preserve backcompat, the addon now allows both type 3 and type 4 articles to be valid root
# folders.
FIGSHARE_FOLDER_TYPES = {3, 4, }
