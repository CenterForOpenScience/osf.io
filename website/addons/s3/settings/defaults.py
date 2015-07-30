import json

MAX_RENDER_SIZE = (1024 ** 2) * 3

ALLOWED_ORIGIN = '*'

BUCKET_LOCATIONS = {
    '': 'US Standard',
    'EU': 'Europe Standard',
    'us-west-1': 'California',
    'us-west-2': 'Oregon',
    'ap-northeast-1': 'Tokyo',
    'ap-southeast-1': 'Singapore',
    'ap-southeast-2': 'Sydney',
    'cn-north-1': 'Beijing'
}
DEFAULT_BUCKET_LOCATION = {
    'value': '',
    'message': 'US Standard'
}

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
