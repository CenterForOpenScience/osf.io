"""
Metadata addon default settings
"""
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
