try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('DATAVERSE_PROVIDER_CONFIG', {})

EDIT_MEDIA_BASE_URL = config.get('EDIT_MEDIA_BASE_URL', "/dvn/api/data-deposit/v1.1/swordv2/edit-media/")
DOWN_BASE_URL = config.get('DOWN_BASE_URL', "/api/access/datafile/")
METADATA_BASE_URL = config.get('METADATA_BASE_URL', "/dvn/api/data-deposit/v1.1/swordv2/statement/study/")
JSON_BASE_URL = config.get('JSON_BASE_URL', "/api/datasets/{0}/versions/:{1}")
