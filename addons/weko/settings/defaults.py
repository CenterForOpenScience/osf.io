
REQUEST_TIMEOUT = 15

REPOSITORIES = {'no_host.repo.nii.ac.jp':
                 {'host': 'http://no_host.repo.nii.ac.jp/weko/sword/',
                  'client_id': None, 'client_secret': None,
                  'authorize_url': None,
                  'access_token_url': None}}
REPOSITORY_IDS = list(sorted(REPOSITORIES.keys()))

DRAFT_DIR = '/tmp/'
