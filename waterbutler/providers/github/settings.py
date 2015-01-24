try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('GITHUB_PROVIDER_CONFIG', {})


BASE_URL = config.get('BASE_URL', 'https://api.github.com/')

UPLOAD_FILE_MESSAGE = config.get('UPLOAD_FILE_MESSAGE', 'File uploaded on behalf of WaterButler')
DELETE_FILE_MESSAGE = config.get('DELETE_FILE_MESSAGE', 'File deleted on behalf of WaterButler')
DELETE_FOLDER_MESSAGE = config.get('DELETE_FOLDER_MESSAGE', 'Folder deleted on behalf of WaterButler')