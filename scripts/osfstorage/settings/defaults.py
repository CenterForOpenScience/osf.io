# encoding: utf-8
import os


USERNAME = 'changeme'
API_KEY = 'changeme'
REGION = 'changeme'

PRIMARY_CONTAINER_NAME = 'primary_container'
PARITY_CONTAINER_NAME = 'parity_container'

# https://boto3.readthedocs.io/en/latest/reference/services/glacier.html#vault
GLACIER_VAULT_ACCOUNT_ID = '-'
GLACIER_VAULT_NAME = 'glacier_vault'

AWS_REGION = 'us-east-1'
AWS_ACCESS_KEY = 'changeme'
AWS_SECRET_KEY = 'changeme'

AUDIT_TEMP_PATH = '/opt/data/files_audit'

GCS_SERVICE_ACCOUNT_JSON = os.path.expanduser('~/service_account.json')
GCS_BUCKET_NAME = 'changeme'
GCS_BACKUP_BUCKET_NAME = 'changeme'
GCS_PARITY_BUCKET_NAME = 'changeme'
