try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('DATAVERSE_PROVIDER_CONFIG', {})

HOSTNAME = config.get('HOSTNAME', 'apitest.dataverse.org')

UP_BASE_URL = config.get('UP_BASE_URL', "https://{0}/dvn/api/data-deposit/v1.1/swordv2/edit-media/study/".format(HOSTNAME))
DOWN_BASE_URL = config.get('DOWN_BASE_URL', "https://{0}/api/access/datafile/".format(HOSTNAME))
METADATA_BASE_URL = config.get('METADATA_BASE_URL', "https://{0}/dvn/api/data-deposit/v1.1/swordv2/statement/study/".format(HOSTNAME))
