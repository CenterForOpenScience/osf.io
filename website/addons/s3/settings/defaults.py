import json
import os

from website.settings import parent_dir


HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(parent_dir(HERE), 'static')

MAX_RENDER_SIZE = (1024 ** 2) * 3

ALLOWED_ORIGIN = '*'

BUCKET_LOCATIONS = {}
# Load S3 bucket key/value map
with open(os.path.join(STATIC_PATH, 'bucketLocations.json')) as fp:
    BUCKET_LOCATIONS = json.load(fp)

DEFAULT_BUCKET_LOCATION = {
    'value': '',
    'message': 'US Standard'
}
ENCRYPT_UPLOADS_DEFAULT = True

OSF_USER = 'osf-user{0}'
OSF_USER_POLICY_NAME = 'osf-user-policy'
OSF_USER_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Stmt1392138408000",
                "Effect": "Allow",
                "Action": [
                    "s3:*"
                ],
                "Resource": [
                    "*"
                ]
            },
            {
                "Sid": "Stmt1392138440000",
                "Effect": "Allow",
                "Action": [
                    "iam:DeleteAccessKey",
                    "iam:DeleteUser",
                    "iam:DeleteUserPolicy"
                ],
                "Resource": [
                    "*"
                ]
            }
        ]
    }
)
