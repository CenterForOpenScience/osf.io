PIWIK_DB_HOST = 'localhost'
PIWIK_DB_PORT = 3336
PIWIK_DB_USER = 'root'
PIWIK_DB_PASSWORD = 'changeme'
PIWIK_DB_NAME = 'piwik_staging'

PROJECT_ID = 'keen-project-id'
WRITE_KEY = 'keen-write-key'


OUTPUT_DIR = 'piwik-migration'

PHASES = {
    'EXTRACT': {
        'DIR': 'extract',
    },
    'TRANSFORM': {
        'DIR': 'transform',
    },
    'LOAD': {
        'DIR': 'load',
    },
}

EXTRACT_FILE = 'extracted.data'
TRANSFORM_FILE = 'transform.data'
LOAD_FILE = 'load.data'

HISTORY_FILENAME = 'history.txt'
COMPLAINTS_FILENAME = 'complaints.txt'
