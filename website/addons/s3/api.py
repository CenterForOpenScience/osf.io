import os

from dateutil.parser import parse

from boto.s3.connection import S3Connection, Key
from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.cors import CORSConfiguration
from boto.exception import S3ResponseError

from hurry.filesize import size, alternative


#Note: (from boto docs) this function is in beta
def enable_versioning(user_settings):
    wrapper = S3Wrapper.from_addon(user_settings)
    wrapper.bucket.configure_versioning(True)


def has_access(access_key, secret_key):
    try:
        c = S3Connection(access_key, secret_key)
        c.get_all_buckets()
        return True
    except Exception:
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
        if not s3.is_registration:
            return cls(S3Connection(s3.user_settings.access_key, s3.user_settings.secret_key), s3.bucket)
        else:
            return RegistrationWrapper(s3)

    @classmethod
    def bucket_exist(cls, s3, bucketName):
        m = cls.fromAddon(s3)
        return not m.connection.lookup(bucketName.lower(), validate=False)

    "S3 Bucket management"

    def __init__(self, connection, bucket_name):
        self.connection = connection
        if bucket_name != bucket_name.lower():
            self.connection.calling_format = OrdinaryCallingFormat()
        self.bucket = self.connection.get_bucket(bucket_name, validate=False)

    def create_key(self, key):
        self.bucket.new_key(key)

    def get_file_list(self, prefix=None):
        if not prefix:
            return self.bucket.list()
        else:
            return self.bucket.list(prefix=prefix)

    def create_folder(self, name, pathToFolder=""):
        if not name.endswith('/'):
            name.append("/")
        k = self.bucket.new_key(pathToFolder + name)
        return k.set_contents_from_string("")

    def delete_file(self, keyName):
        return self.bucket.delete_key(keyName)

    def download_file_URL(self, keyName, vid=None):
        return self.bucket.get_key(keyName, version_id=vid, headers={'Content-Disposition': 'attachment'}).generate_url(5)

    def get_wrapped_keys(self, prefix=None):
        return [S3Key(x) for x in self.get_file_list()]

    def get_wrapped_key(self, key_name, vid=None):
        """Get S3 key.

        :param str key_name: Name of S3 key
        :param str version_id: Optional file version
        :return: Wrapped S3 key if found, else None

        """
        try:
            key = self.bucket.get_key(key_name, version_id=vid)
            if key is not None:
                return S3Key(key)
            return None
        except S3ResponseError:
            return None

    def get_wrapped_keys_in_dir(self, directory=None):
        return [S3Key(x) for x in self.bucket.list(delimiter='/', prefix=directory) if isinstance(x, Key) and x.key != directory]

    def get_wrapped_directories_in_dir(self, directory=None):
        return [S3Key(x) for x in self.bucket.list(prefix=directory) if isinstance(x, Key) and x.key.endswith('/') and x.key != directory]

    @property
    def bucket_name(self):
        return self.bucket.name

    def get_version_data(self):
        versions = {}
        versions_list = self.bucket.list_versions()
        for p in versions_list:
            if isinstance(p, Key) and str(p.version_id) != 'null' and str(p.key) not in versions:
                versions[str(p.key)] = [str(k.version_id)
                                        for k in versions_list if p.key == k.key]
        return versions
        # TODO update this to cache results later

    def get_file_versions(self, file_name):
        return [x for x in self.bucket.list_versions(prefix=file_name) if isinstance(x, Key)]

    def get_cors_rules(self):
        try:
            return self.bucket.get_cors()
        except:
            return CORSConfiguration()

    def set_cors_rules(self, rules):
        return self.bucket.set_cors(rules)

    def does_key_exist(self, key_name):
        return self.bucket.get_key(key_name) is not None


# TODO Add null checks etc
class RegistrationWrapper(S3Wrapper):

    def __init__(self, node_settings):
        if node_settings.user_settings:
            connection = S3Connection(
                node_settings.user_settings.access_key,
                node_settings.user_settings.secret_key,
            )
        else:
            connection = S3Connection()
        super(RegistrationWrapper, self).__init__(connection, node_settings.bucket)
        self.registration_data = node_settings.registration_data

    def get_wrapped_keys_in_dir(self, directory=None):
        return [
            S3Key(x)
            for x in self.bucket.list_versions(delimiter='/', prefix=directory)
            if isinstance(x, Key) and x.key != directory
                and self.is_right_version(x)
        ]

    def get_wrapped_directories_in_dir(self, directory=None):
        return [S3Key(x) for x in self.bucket.list_versions(prefix=directory) if self._directory_check(x, directory)]

    def _directory_check(self, to_check, against):
        return isinstance(to_check, Key) and to_check.key.endswith('/') and to_check.key != against and self.is_right_version(to_check)

    def is_right_version(self, key):
        return [x for x in self.registration_data['keys'] if x['version_id'] == key.version_id and x['path'] == key.key]

    def get_file_versions(self, key_name):
        to_cut = [x for x in self.bucket.list_versions(
            prefix=key_name) if isinstance(x, Key)]
        return to_cut[self._get_index_of(self._get_proper_version(key_name), to_cut):]

    def _get_proper_version(self, key_name):
        vid = [x['version_id']
               for x in self.registration_data['keys'] if x['path'] == key_name][0]
        return self.bucket.get_key(key_name, version_id=vid)

    def _get_index_of(self, version, to_cut):
        return to_cut.index([x for x in to_cut if x.version_id == version.version_id][0])


# TODO Extend me and you bucket.setkeyclass
class S3Key(object):

    def __init__(self, key):
        self.s3Key = key
        if self.type == 'file':
            self.versions = ['current']
        else:
            self.versions = None

    @property
    def name(self):
        d = self.s3Key.key.split('/')
        if len(d) > 1 and self.type == 'file':
            return d[-1]
        elif self.type == 'folder':
            return d[-2]
        else:
            return d[0]

    @property
    def type(self):
        if not self.s3Key.key.endswith('/'):
            return 'file'
        else:
            return 'folder'

    @property
    def parentFolder(self):
        d = self.s3Key.key.split('/')

        if len(d) > 1 and self.type == 'file':
            return d[len(d) - 2]
        elif len(d) > 2 and self.type == 'folder':
            return d[len(d) - 3]
        else:
            return None

    @property
    def pathTo(self):
        return self.s3Key.key[:self.s3Key.key.rfind('/')] + '/'

    @property
    def size(self):
        if self.type == 'folder':
            return None
        else:
            return size(float(self.s3Key.size), system=alternative)

    @property
    def lastMod(self):
        if self.type == 'folder':
            return None
        else:
            return parse(self.s3Key.last_modified)

    @property
    def version(self):
        return self.versions

    @property
    def extension(self):
        if self.type != 'folder':
            if os.path.splitext(self.s3Key.key)[1] is None:
                return None
            else:
                return os.path.splitext(self.s3Key.key)[1][1:]
        else:
            return None

    @property
    def md5(self):
        return self.s3Key.md5

    @property
    def version_id(self):
        return self.s3Key.version_id if self.s3Key.version_id != 'null' else 'Pre-versioning'

    def updateVersions(self, manager):
        if self.type != 'folder':
            self.versions.extend(manager.get_file_versions(self.s3Key.key))

    @property
    def etag(self):
        return self.s3Key.etag.replace('"', '')
