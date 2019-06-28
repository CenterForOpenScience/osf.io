from bidict import bidict

CLIENT_ID = None
CLIENT_SECRET = None

API_BASE_URL = 'https://api.figshare.com/v2/'

MAX_RENDER_SIZE = 1000

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 50

FIGSHARE_OAUTH_TOKEN_ENDPOINT = '{}{}'.format(API_BASE_URL, 'token')
FIGSHARE_OAUTH_AUTH_ENDPOINT = 'https://figshare.com/account/applications/authorize'

# Each figshare article has a `defined_type` integer and a matching `defined_type_name` string. A
# bi-directional dictionary (https://bidict.readthedocs.io/en/master/) is used here since both the
# type and name are used in the figshare client.  In addition, check with figshare occasionally
# for changes such as type deprecation, type name update as well as new types.
#
# TODO: refactor the client to use the `defined_type` only since figshare does change the names :(
#
FIGSHARE_DEFINED_TYPE_MAP = bidict({
    'figure': 1,
    'media': 2,
    'dataset': 3,
    'fileset': 4,  # Unofficially deprecated and replaced by type 3 dataset
    'poster': 5,
    'journal contribution': 6,
    'presentation': 7,
    'thesis': 8,
    'software': 9,
    # For unknown reasons, 10 does not exist
    'online resource': 11,
    'preprints': 12,
    'book': 13,
    'conference': 14,
})

# figshare used to only let type 4 fileset to behave like folders, i.e. it can contain multiple
# files.  However, it suddenly changed without any announcement that all article types are now
# folder-like and that type 4 fileset is unofficially deprecated and converted to type 3 dataset
# internally.  In order not to break the old behavior of OSF and WB, we decide for now to only
# treat dataset and fileset as folders.
#
# TODO: refactor the figshare client to treat all article types as folders
#
FIGSHARE_FOLDER_TYPES = {3, 4, }
