__author__ = 'Chris Seto'


from os.path import basename

from boto.exception import *
from boto.s3.connection import *
from boto.s3.cors import CORSConfiguration

from hurry.filesize import size

import os
import re
from boto.iam import *
import json
from datetime import datetime
from urllib import quote




def has_access(access_key, secret_key):
    try:
        c = S3Connection(access_key,secret_key)
        c.get_all_buckets()
        return True
    except Exception:
        return False

def create_limited_user(accessKey, secretKey,bucketName):
    policy = {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1389718377000",
      "Effect": "Allow",
      "Action": [
        "s3:AbortMultipartUpload",
        "s3:CreateBucket",
        "s3:DeleteBucketPolicy",
        "s3:DeleteBucketWebsite",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:GetBucketAcl",
        "s3:GetBucketLocation",
        "s3:GetBucketLogging",
        "s3:GetBucketNotification",
        "s3:GetBucketPolicy",
        "s3:GetBucketRequestPayment",
        "s3:GetBucketTagging",
        "s3:GetBucketVersioning",
        "s3:GetBucketWebsite",
        "s3:GetLifecycleConfiguration",
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:GetObjectTorrent",
        "s3:GetObjectVersion",
        "s3:GetObjectVersionAcl",
        "s3:GetObjectVersionTorrent",
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:ListBucketVersions",
        "s3:ListMultipartUploadParts",
        "s3:PutBucketAcl",
        "s3:PutBucketLogging",
        "s3:PutBucketNotification",
        "s3:PutBucketPolicy",
        "s3:PutBucketRequestPayment",
        "s3:PutBucketTagging",
        "s3:PutBucketVersioning",
        "s3:PutBucketWebsite",
        "s3:PutLifecycleConfiguration",
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:PutObjectVersionAcl"
      ],
      "Resource": [
        "arn:aws:s3:::{bucketname}/*".format(bucketname=bucketName)
      ]
    }
  ]
}
    connection = IAMConnection(accessKey,secretKey)
    try:
        connection.create_user(bucketName + '-osf-limited')
    except Exception:
        pass
        #user has been created already proceed normally
        #TODO update me I may cause BIG problems
    connection.put_user_policy(bucketName + '-osf-limited','policy-' + bucketName + '-osf-limited',json.dumps(policy))
    return connection.create_access_key(bucketName + '-osf-limited')['create_access_key_response']['create_access_key_result']['access_key'] 

def remove_user(accessKey, secretKey,bucketName,otherKey):
    connection = IAMConnection(accessKey, secretKey)
    connection.delete_user_policy(bucketName + '-osf-limited','policy-'+bucketName + '-osf-limited')
    connection.delete_access_key(otherKey,bucketName + '-osf-limited')
    connection.delete_user(bucketName + '-osf-limited')

def does_bucket_exist(accessKey, secretKey,bucketName):
    try:
        c = S3Connection(accessKey,secretKey)
        c.get_bucket(bucketName)
        return True
    except Exception:
        return False

class S3Wrapper:

    @classmethod
    def from_addon(cls,s3):
        return cls(S3Connection(s3.user_settings.access_key,s3.user_settings.secret_key),s3.s3_bucket)

    @classmethod
    def bucket_exist(cls,s3, bucketName):
        m = cls.fromAddon(s3)
        try:
            m.connection.get_bucket(bucketName.lower())
            return True
        except Exception:
            return False

    "S3 Bucket management"
    def __init__(self, connect,bucketName):
        self.connection = connect
        self.bucket = self.connection.get_bucket(bucketName)

    def create_key(self,key):
        self.bucket.new_key(key)

    def post_string(self,title,contentspathToFolder=""):
        k = self.bucket.new_key(pathToFolder + title)
        return k.set_contents_from_string(contents)

    def get_string(self,title):
        return self.bucket.get_key(title).get_contents_as_string()

    def set_metadata(self,bucket,key,metadataName,metadata):
        k = self.connection.get_bucket(bucket).get_key(key)
        return k.set_metadata(metadataName,metadata)

    def get_file_list(self):
        return self.bucket.list()
        
    def create_folder(self,name,pathToFolder=""):
        if not name.endswith('/'):
            name.append("/")
        k = self.bucket.new_key(pathToFolder + name)
        return k.set_contents_from_string("")

    def delete_file(self,keyName):
        return self.bucket.delete_key(keyName)

    def get_MD5(self,keyName):
        '''returns the MD5 hash of a file.

        params str keyName: The name of the key to hash

        '''
        return self.bucket.get_key(keyName).get_md5_from_hexdigest()

    def download_file_URL(self,keyName):
        return self.bucket.get_key(keyName).generate_url(5)

    def get_wrapped_keys(self):
        return [S3Key(x) for x in self.get_file_list()]

    def get_wrapped_key(self,keyName):
        return S3Key(self.bucket.get_key(keyName))

    @property
    def bucket_name(self):
        return self.bucket.name

    def get_version_data(self):
        versions = {}
        versions_list = self.bucket.list_versions()
        for p in versions_list:
            if isinstance(p,Key) and str(p.version_id) != 'null' and str(p.key) not in versions:
                versions[str(p.key)] = [str(k.version_id) for k in versions_list if p.key == k.key]
        return versions
        #TODO update this to cache results later

    def get_file_versions(self,fileName):
        v = self.get_version_data() #TODO store list in self and check for changes
        if fileName in v:
            return v[fileName]
        return []

    def get_cors_rules(self):
        try:
            return self.bucket.get_cors()
        except:
            return CORSConfiguration()

    def set_cors_rules(self,rules):
        return self.bucket.set_cors(rules)


#TODO Extend me and you bucket.setkeyclass
class S3Key:

    def __init__(self, key):
        self.s3Key = key
        if self.type == 'file':
            self.versions = ['current']
        else:
            self.version =  None

    @property
    def name(self):
        d = self._nameAsStr().split('/')
        if len(d) > 1 and self.type == 'file':
            return d[-1]
        elif self.type == 'folder':
            return d[-2]
        else:
            return d[0]

    def _nameAsStr(self):
        return str(self.s3Key.key)

    @property
    def type(self):
        if not str(self.s3Key.key).endswith('/'):
            return 'file'
        else:
            return 'folder'

    @property
    def fullPath(self):
        return self._nameAsStr()

    @property
    def parentFolder(self):
        d = self._nameAsStr().split('/')

        if len(d) > 1 and self.type == 'file':
            return d[len(d)-2]
        elif len(d) > 2 and self.type == 'folder':
            return d[len(d)-3]
        else:
            return None

    @property
    def pathTo(self):
        return self._nameAsStr()[:self._nameAsStr().rfind('/')] + '/'

    @property
    def size(self):
        if self.type == 'folder':
            return None
        else:
            return size(int(self.s3Key.size)).lower()
    @property
    def lastMod(self):
        if self.type == 'folder':
            return None
        else:
            m= re.search('(.+?)-(.+?)-(\d*)T(\d*):(\d*):(\d*)',str(self.s3Key.last_modified))
            if m is not None:
                return datetime(int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(5)))
            else:
                return None

    @property
    def version(self):
        return self.versions

    @property
    def extension(self):
        if self.type != 'folder':
            if os.path.splitext(self._nameAsStr())[1] is None:
                return None
            else:
                return os.path.splitext(self._nameAsStr())[1][1:]
        else:
            return None

    def updateVersions(self, manager):
        if self.type != 'folder':
            self.versions.extend(manager.get_file_versions(self._nameAsStr()))
