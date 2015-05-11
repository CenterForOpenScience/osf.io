from boto.s3.connection import S3Connection
from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.cors import CORSConfiguration

from boto.exception import S3ResponseError

def has_access(access_key, secret_key):
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (access_key and secret_key):
        return False

    try:
        c = S3Connection(access_key, secret_key)
        c.get_all_buckets()
        return True
    except S3ResponseError:
        return False


def get_bucket_list(user_settings):
        return S3Connection(user_settings.access_key, user_settings.secret_key).get_all_buckets()


def create_bucket(user_settings, bucket_name):
    connect = S3Connection(
        user_settings.access_key, user_settings.secret_key)
    return connect.create_bucket(bucket_name)


def does_bucket_exist(accessKey, secretKey, bucketName):
    try:
        c = S3Connection(accessKey, secretKey)
        c.get_bucket(bucketName, validate=False)
        return True
    except Exception:
        return False


class S3Wrapper(object):

    @classmethod
    def from_addon(cls, s3):
        if s3 is None or s3.user_settings is None:
            return None
        return cls(S3Connection(s3.user_settings.access_key, s3.user_settings.secret_key), s3.bucket)

    "S3 Bucket management"

    def __init__(self, connection, bucket_name):
        self.connection = connection
        if bucket_name != bucket_name.lower():
            self.connection.calling_format = OrdinaryCallingFormat()
        self.bucket = self.connection.get_bucket(bucket_name, validate=False)

    @property
    def bucket_name(self):
        return self.bucket.name

    def get_cors_rules(self):
        try:
            return self.bucket.get_cors()
        except:
            return CORSConfiguration()

    def set_cors_rules(self, rules):
        return self.bucket.set_cors(rules)
