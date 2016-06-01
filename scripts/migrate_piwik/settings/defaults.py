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
    'TRANSFORM01': {
        'DIR': 'transform-01',
    },
    'TRANSFORM02': {
        'DIR': 'transform-02',
    },
    'LOAD': {
        'DIR': 'load',
    },
}

EXTRACT_FILE = 'extracted.data'
TRANSFORM01_FILE = 'transform-01.data'
LOAD_FILE = 'load.data'

HISTORY_FILENAME = 'history.txt'
COMPLAINTS_FILENAME = 'complaints.txt'
RUN_HEADER = 'Run ID: '

BATCH_SIZE = 5000

ES_INDEX = 'piwik-migration-test'
