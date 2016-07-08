import json
import os

from website.settings import parent_dir


HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(parent_dir(HERE), 'static')

MAX_RENDER_SIZE = (1024 ** 2) * 3

ALLOWED_ORIGIN = '*'

BUCKET_LOCATIONS = {}
ENCRYPT_UPLOADS_DEFAULT = True
# Load S3 settings used in both front and back end
with open(os.path.join(STATIC_PATH, 'settings.json')) as fp:
    settings = json.load(fp)
    BUCKET_LOCATIONS = settings.get('bucketLocations', {})
    ENCRYPT_UPLOADS_DEFAULT = settings.get('encryptUploads', True)

OSF_USER = 'osf-user{0}'
OSF_USER_POLICY_NAME = 'osf-user-policy'
OSF_USER_POLICY = json.dumps(
    {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'Stmt1392138408000',
                'Effect': 'Allow',
                'Action': [
                    's3:*'
                ],
                'Resource': [
                    '*'
                ]
            },
            {
                'Sid': 'Stmt1392138440000',
                'Effect': 'Allow',
                'Action': [
                    'iam:DeleteAccessKey',
                    'iam:DeleteUser',
                    'iam:DeleteUserPolicy'
                ],
                'Resource': [
                    '*'
                ]
            }
        ]
    }
)
