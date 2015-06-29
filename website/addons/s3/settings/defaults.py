import json

MAX_RENDER_SIZE = (1024 ** 2) * 3

ALLOWED_ORIGIN = '*'

VALID_BUCKET_LOCATIONS = [
    '',
    'EU',
    'us-west-1',
    'us-west-2',
    'ap-northeast-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'cn-north-1'
]

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
