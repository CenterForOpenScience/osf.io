__author__ = 'Chris Seto'


from os.path import basename

from boto.exception import *
from boto.s3.connection import *

from hurry.filesize import size

import os
import re
from boto.iam import *
import json



URLADDONS = {
        'delete':'delete/',
        'upload':'upload/',
        'download':'download/',
}

def testAccess(access_key, secret_key):
    try:
        c = S3Connection(access_key,secret_key)
        c.get_all_buckets()
        return True
    except Exception:
        return False

def createLimitedUser(accessKey, secretKey,bucketName):
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
    connection.create_user(bucketName + '-osf-limited')
    connection.put_user_policy(bucketName + '-osf-limited','policy-' + bucketName + '-osf-limited',json.dumps(policy))
    return connection.create_access_key(bucketName + '-osf-limited')['create_access_key_response']['create_access_key_result']['access_key'] 

def removeUser(accessKey, secretKey,bucketName,otherKey):
    connection = IAMConnection(accessKey, secretKey)
    connection.delete_user_policy(bucketName + '-osf-limited','policy-'+bucketName + '-osf-limited')
    connection.delete_access_key(otherKey,bucketName + '-osf-limited')
    connection.delete_user(bucketName + '-osf-limited')

def doesBucketExist(accessKey, secretKey,bucketName):
    try:
        c = S3Connection(accessKey,secretKey)
        c.get_bucket(bucketName)
        return True
    except Exception:
        return False

class BucketManager:

    @staticmethod
    def fromAddon(s3):
        return BucketManager(S3Connection(s3.user_settings.access_key,s3.user_settings.secret_key),s3.s3_bucket)

    @staticmethod
    def bucketExist(s3, bucketName):
        m = BucketManager.fromAddon(s3)
        try:
            m.connection.get_bucket(bucketName.lower())
            return True
        except Exception:
            return False

    "S3 Bucket management"
    def __init__(self, connect,bucketName):
        self.connection = connect
        self.bucket = self._getBucket(bucketName)

    @staticmethod
    def getLoctions(self):
        print '\n'.join(i for i in dir(Location) if i[0].isupper())

    def _newBucket(self, name,location=Location.DEFAULT):
        try:
            self.connection.create_bucket(name.lower(),location)
        except S3CreateError:
            print "S3CreateError: Bucket name already in use."


    def _getBucket(self,bucketName):
        try:
            return self.connection.get_bucket(bucketName.lower())
        except S3PermissionsError:
            print S3PermissionsError.message

    def _listBuckets(self):
       list = self.connection.get_all_buckets()
       for bucket in list:
            print bucket

    def createKey(self,key,bucket):
        Key(self[bucket]).key = key

    def uploadFile(self,fileName,pathToFolder=""):
        k = self.bucket.new_key(pathToFolder + basename(fileName))
        k.set_contents_from_filename(fileName)

    def downloadFile(self,fileName):
         #Broken and or depricated
         #TODO Remove
        k.key = fileName
       # k.get_contents_to_file(open("/Users/nan/Downloads/" + fileName,'a'))

    def postString(self,title,contentspathToFolder=""):
        k = self.bucket.new_key(pathToFolder + title)
        k.set_contents_from_string(contents)

    def getString(self,title):
        return self.bucket.get_key(title).get_contents_as_string()

    def setMetadata(self,bucket,key,metadataName,metadata):
        k = self.connection.get_bucket(bucket).get_key(key)
        k.set_metadata(metadataName,metadata)

    def getFileList(self):
            return self.bucket.list()
        
    def createFolder(self,name,pathToFolder=""):
        k = self.bucket.new_key(pathToFolder + name + "/")
        k.set_contents_from_string("")


    def deleteFile(self,keyName):
            self.bucket.delete_key(keyName)

    def getMD5(self,keyName):
        return self.bucket.get_key(keyName).get_md5_from_hexdigest()

    def downloadFileURL(self,keyName):
        return self.bucket.get_key(keyName).generate_url(5)

    def getWrappedKeys(self, bucketList):
        List = []
        for k in bucketList:
            List.append(S3Key(k))
        return List

    def getWrappedKey(self,keyName):
        return S3Key(self.bucket.get_key(keyName))

    def getHgrid(self,url):
            keyList = self.getWrappedKeys(self.bucket.list())
            hgrid = []
            hgrid.append({
            'uid': 0,
            'name': str(self.bucket.name),
            'type': 'folder',
            'parent_uid': 'null',
            'version_id': '--',
            'lastMod': '--',
            'size':'--',
            'uploadUrl': url + URLADDONS['upload'],
            'downloadUrl':url + URLADDONS['download'],
            'deleteUrl':url + URLADDONS['delete'],
            })
            self.checkFolders(keyList)
            for k in keyList:
                k.updateVersions(self)
                if k.parentFolder is not 'null':
                    q = [x for x in keyList if k.parentFolder == x.name]
                    hgrid.append(k.getAsDict(url,q[0].fullPath))
                else:
                    hgrid.append(k.getAsDict(url))
            return hgrid

    def checkFolders(self,keyList):
        for k in keyList:
            if k.parentFolder is not 'null' and k.parentFolder not in [x.name for x in keyList]:
                newKey = self.bucket.new_key(k.pathTo)
                newKey.set_contents_from_string("")
                keyList.append(S3Key(newKey))
                raise Exception

    def flaskUpload(self,upFile,safeFilename,parentFolder=None):
        if parentFolder:
            k = self.bucket.new_key(parentFolder + safeFilename)
        else:
            k = self.bucket.new_key(safeFilename)
        k.set_contents_from_string(upFile.read())

    def getVersionData(self):
        versions = {}
        for p in self.bucket.list_versions():
            if type(p) is Key:
                if str(p.version_id) != 'null':
                    if str(p.key) not in versions:
                        versions[str(p.key)] = []
                    versions[str(p.key)].append(str(p.version_id))
        return versions
        #update this to cache results later

    def getFileVersions(self,fileName):
        v = self.getVersionData()
        if fileName in v:
            return v[fileName]
        return []

class S3Key:


    def __init__(self, key):
        self.s3Key = key
        if self.type is 'file':
            self.versions = ['current']
        else:
            self.version =  '--'

    @property
    def name(self):
        d = self._nameAsStr().split('/')
        if len(d) > 1 and self.type is 'file':
            return d[len(d)-1]
        elif self.type is 'folder':
            return d[len(d)-2]
        else:
            return d[0]

    def _nameAsStr(self):
        return str(self.s3Key.key)

    @property
    def type(self):
        if not (str(self.s3Key.key).endswith('/')):
            return 'file'
        else:
            return 'folder'

    @property
    def fullPath(self):
        return self._nameAsStr()

    @property
    def parentFolder(self):
        d = self._nameAsStr().split('/')

        if len(d) > 1 and self.type is 'file':
            return d[len(d)-2]
        elif len(d) > 2 and self.type is 'folder':
            return d[len(d)-3]
        else:
            return 'null'
    def getAsDict(self,url,parent_uid=0):
        return{
            'uid': self.fullPath,
            'type':self.type,
            'name':self.name,
            'parent_uid':parent_uid,
            'version_id':self.version,
            'size':self.size,
            'lastMod':self.lastMod,
            'ext':self.extention,
            'uploadUrl': self.uploadPath(url),
            'downloadUrl':url + URLADDONS['download'],
            'deleteUrl':url + URLADDONS['delete'],
        }
    @property
    def pathTo(self):
        return self._nameAsStr()[:self._nameAsStr().rfind('/')] + '/'

    @property
    def size(self):
        if self.type is 'folder':
            return '--'
        else:
            return size(int(self.s3Key.size)).lower()
    @property
    def lastMod(self):
        if self.type is 'folder':
            return '--'
        else:
            m= re.search('(.+?)-(.+?)-(\d*)T(\d*):(\d*):(\d*)',str(self.s3Key.last_modified))
            if(m is not None):
                return "{month}/{day}/{year} {hour}:{minute}".format(month=m.group(2),day=m.group(3),year=m.group(4),hour=m.group(5),minute=m.group(6))
            else:
                return '--'

    @property
    def version(self):
        return self.versions

    @property
    def extention(self):
        if self.type is not 'folder':
            if os.path.splitext(self._nameAsStr())[1] is None:
                return '--'
            else:
                return os.path.splitext(self._nameAsStr())[1][1:]
        else:
            return '--'
    def updateVersions(self, manager):
        if self.type is not 'folder':
            self.versions.extend(manager.getFileVersions(self._nameAsStr()))

    def uploadPath(self,url):
        if self.type is not 'folder':
            return url + URLADDONS['upload']
        else:
            return url + URLADDONS['upload'] + self.fullPath.replace(' ','&spc').replace('/','&sl') + '/'