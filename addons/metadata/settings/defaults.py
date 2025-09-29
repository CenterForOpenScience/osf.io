"""
Metadata addon default settings
"""
import os
USE_EXPORTING = False
USE_DATASET_IMPORTING = False

# Maximum size of files that can be exported ... 1GB
MAX_EXPORTABLE_FILES_BYTES = 1024 * 1024 * 1024

METADATA_ASSET_POOL_BASE_PATH = '.metadata'
METADATA_ASSET_POOL_MAX_FILESIZE = 1024 * 1024 * 10  # 10MB

# Maximum size of a dataset that can be imported ... 1GB
MAX_IMPORTABLE_DATASET_HTML_BYTES = 1024 * 1024 * 10  # 10MB
MAX_IMPORTABLE_DATASET_DATA_BYTES = 1024 * 1024 * 1024  # 1GB
DEFAULT_DATASET_TIMEOUT = 60  # seconds

# List of addons that are not allowed to be exported
EXCLUDED_ADDONS_FOR_EXPORT = ['mendeley', 'zotero', 'iqbrims']
EXCLUDED_ADDONS_FOR_EXPORT += ['dropboxbusiness', 'nextcloudinstitutions', 'ociinstitutions', 'onedrivebusiness', 's3compatinstitutions']


# KAKEN Elasticsearch settings
# If None, KAKEN functionality is disabled
KAKEN_ELASTIC_URI = os.getenv('KAKEN_ELASTIC_URI')
KAKEN_ELASTIC_INDEX = 'kaken_researchers'
KAKEN_ELASTIC_KWARGS = {
    'use_ssl': False,
    'verify_certs': True,
    'max_retries': 3,
    'retry_on_timeout': True
}

# ResourceSync settings for KAKEN
KAKEN_RESOURCESYNC_URL = 'https://nrid.nii.ac.jp/.well-known/resourcesync'

# Batch processing control
KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION = 10000  # Maximum documents to process per execution

# Elasticsearch analyzer configuration for KAKEN
# Note: Using standard analyzer since kuromoji plugin is not available in this environment
KAKEN_ELASTIC_ANALYZER_CONFIG = {
    'analysis': {
        'analyzer': {
            'kuromoji_analyzer': {
                'type': 'custom',
                'tokenizer': 'standard',
                'filter': ['cjk_width', 'lowercase']
            }
        }
    }
}
