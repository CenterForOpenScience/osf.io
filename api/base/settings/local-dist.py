# API_PATH is '/api' on staging/production, '' on develop
API_PATH = ''
API_BASE = 'v2/'

STATIC_URL = '{}/{}static/'.format(API_PATH, API_BASE)
