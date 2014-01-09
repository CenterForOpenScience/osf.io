__author__ = 'Chris Seto'


from os.path import basename

from boto.exception import *
from boto.s3.connection import *

from hurry.filesize import size

import os


class BucketManager:
    "S3 Bucket management"
    def __init__(self, connect=S3Connection,bucketName=None):
        self.connection = connect
        if bucketName is not None:
            self.__defaultBucket = self.getBucket(bucketName)
        else:
            if(len(self.connection.get_all_buckets()) == 0):
                self.newBucket("DefaultBucket")
            else:
                self.__defaultBucket = self.connection.get_all_buckets()[1]

    @staticmethod
    def getLoctions(self):
        print '\n'.join(i for i in dir(Location) if i[0].isupper())

    def __getProperBucket(self,bucket):
        if(bucket is None):
            return self.__defaultBucket
        else:
            return self[bucket]

    def newBucket(self, name,location=Location.DEFAULT):
        try:
            self.connection.create_bucket(name.lower(),location)
        except S3CreateError:
            print "S3CreateError: Bucket name already in use."

    def changeDefaultBucket(self,bucketName):
        try:
            self.__defaultBucket = self[bucketName]
        except Exception:
            self.newBucket(bucketName)
            self.__defaultBucket = self[bucketName]

    def getBucket(self,bucketName):
        try:
            return self.connection.get_bucket(bucketName.lower())
        except S3PermissionsError:
            print S3PermissionsError.message

    def __getitem__(self, item):
        return self.getBucket(item)

    def listBuckets(self):
       list = self.connection.get_all_buckets()
       for bucket in list:
            print bucket

    def createKey(self,key,bucket):
        Key(self[bucket]).key = key

    def uploadFile(self,fileName,bucket=None,pathToFolder=""):
        if(bucket is None):
            k = Key(self.__defaultBucket)
        else:
            k = Key(self[bucket])
        k.key = pathToFolder + basename(fileName)
        k.set_contents_from_filename(fileName)

    def downloadFile(self,fileName,bucket=None):
        if(bucket is None):
            k = Key(self.__defaultBucket)
        else:
            k = Key(self[bucket])
        k.key = fileName
        k.get_contents_to_file(open("/Users/nan/Downloads/" + fileName,'a'))

    def postString(self,title,contents,bucket=None,pathToFolder=""):
        if(bucket is None):
            k = Key(self.__defaultBucket)
        else:
            k = Key(self[bucket])
        k.key = pathToFolder + title
        k.set_contents_from_string(contents)

    def getString(self,title,bucket=None):
        if(bucket is None):
            k = Key(self.__defaultBucket)
        else:
            k = Key(self[bucket])
        k.key = title
        return k.get_contents_as_string()

    def setMetadata(self,bucket,key,metadataName,metadata):
        k = self.connection.get_bucket(bucket).get_key(key)
        k.set_metadata(metadataName,metadata)

    def getFileList(self,bucket = None):
        if(bucket is None):
            return self.__defaultBucket.list()
        
        for key in bucket:
            pass

    def createFolder(self,name,bucket=None,pathToFolder=""):
        if(bucket is None):
            k = Key(self.__defaultBucket)
        else:
            k = Key(self[bucket])
        k.key = pathToFolder + name + "/"
        k.set_contents_from_string("")


    def deleteKey(self,keyName,bucket):
        if(bucket is None):
            self.__defaultBucket.delete_key(keyName)
        else:
            bucket.delete_key(keyName)

    def getMD5(self,keyName,bucket = None):
        bucket = self.__getProperBucket(bucket)
        return bucket.get_key(keyName).get_md5_from_hexdigest()

    def downloadFileURL(self,keyName,bucket = None):
        bucket = self.__getProperBucket(bucket)
        return bucket.get_key(keyName).generate_url(5)

    def getWrappedKeys(self, bucketList):
        List = []
        for k in bucketList:
            List.append(S3Key(k))
        return List


    def getFileListAsHGrid(self,bucket = None):
        '''
        {
        'uid':X, 
        'type':"", 
        'name':"", 
        'parent_uid':Y}
        '''
        bucket = self.__getProperBucket(bucket)
        bucketList = bucket.list()
        folders = self._getFolders(bucketList)
        files = []
        parent =  {
            'uid': 0,
            'name': str(bucket.name),
            'type': 'folder',
            'parent_uid': 'null'
        }
        folders.append(parent)

        i = len(folders)



        for k in bucketList:

            s = str(k.key)
            if not s.endswith('/'):
                row = {
                'uid':0,
                'name':'null',
                'type':'null',
                'parent_uid': 0
                }
                row['name'] = s[s.rfind('/')+1:]
                row['uid'] = i
                i+=1

                row['type'] = 'file'
                d = s.split('/')
               # if len(d) > 1:
                       # q = (x for x in folders if x['name'] == d[len(d)-2]).next()
                       # if q:
                        #    row['parent_uid']=q['uid']
               
                files.append(row)

        folders.extend(files)
        return folders


    def _getFolders(self,bucketList):
        folders = []
        i = 1
        for k in bucketList:

            row = {
            'uid':i,
            'name':'null',
            'type':'folder',
            'parent_uid':0
             }
        
            row['uid'] = i
            s1 = str(k.key)
            d = s1.split('/')

            for l  in d[:len(d)-1]:
                if l not in [x['name'] for x in folders]:
                    row['name']=l
                    #if len(d) > 1:
                       # q = (x for x in folders if x['name'] == d[len(d)-2]).next()
                       # if q:
                         #   row['parent_uid']=q['uid']
                    folders.append(row)
                    i+=1
        return folders

    def getHgrid(self,bucket=None):
            S3Key.nextUid = 1
            bucket = self.__getProperBucket(bucket)
            keyList = self.getWrappedKeys(bucket.list())
            hgrid = []
            hgrid.append({
            'uid': 0,
            'name': str(bucket.name),
            'type': 'folder',
            'parent_uid': 'null'
            })
            self.checkFolders(keyList)
            for k in keyList:
                if k.parentFolder is not 'null':
                    q = [x for x in keyList if k.parentFolder == x.name]
                    hgrid.append(k.getAsDict(q[0].uid))
                else:
                    hgrid.append(k.getAsDict())
            return hgrid

    def checkFolders(self,keyList):
        for k in keyList:
            if k.parentFolder is not 'null' and k.parentFolder not in [x.name for x in keyList]:
                newKey = self.__defaultBucket.new_key(k.pathTo)
                newKey.set_contents_from_string("")
                keyList.append(S3Key(newKey))
                raise Exception

class S3Key:

    nextUid = 1

    def __init__(self, key):
        self.s3Key = key
        self.uid = S3Key.nextUid
        S3Key.nextUid+=1

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
    def getAsDict(self,parent_uid=0):
        return{
            'uid':self.uid,
            'type':self.type,
            'name':self.name,
            'parent_uid':parent_uid,
            'version_id':self.version,
            'size':self.size,
            'lastMod':self.lastMod
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
        return str(self.s3Key.last_modified)

    @property
    def version(self):
        if self.s3Key.version_id:
            return str(self.s3Key.version_id)
        else:
            return '--'