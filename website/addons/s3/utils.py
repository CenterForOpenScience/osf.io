from api import S3Wrapper,S3Key
from urllib import quote



URLADDONS = {
        'delete':'delete/',
        'upload':'upload/',
        'download':'download/',
}

def getHgrid(url,s3wrapper):
    keyList = s3wrapper.getWrappedKeys()
    hgrid = []
    hgrid.append({
    'uid': 0,
    'name': str(s3wrapper.bucket_name),
    'type': 'folder',
    'parent_uid': 'null',
    'version_id': '--',
    'lastMod': '--',
    'size':'--',
    'uploadUrl': url + URLADDONS['upload'],
    'downloadUrl':url + URLADDONS['download'],
     'deleteUrl':url + URLADDONS['delete'],
    })
    #checkFolders(s3wrapper,keyList)
    for k in keyList:
        #k.updateVersions(self) #TODO fix versioning
        if k.parentFolder is not None:
            q = [x for x in keyList if k.parentFolder == x.name]
            hgrid.append(wrapped_key_to_json(k,url,q[0].fullPath))
        else:
            hgrid.append(wrapped_key_to_json(k,url))
    return hgrid

def checkFolders(s3wrapper, keyList):
    for k in keyList:
        if k.parentFolder != 'null' and k.parentFolder not in [x.name for x in keyList]:
            newKey = s3wrapper.createFolder(k.pathTo)
            keyList.append(S3Key(newKey))

def wrapped_key_to_json(wrapped_key,url,parent_uid=0):



    return {
    'uid': wrapped_key.fullPath,
    'type':wrapped_key.type,
    'name':wrapped_key.name,
    'parent_uid':parent_uid,
    'version_id':wrapped_key.version if wrapped_key.version is not None else '--',
    'size':wrapped_key.size if wrapped_key.size is not None else '--',
    'lastMod':wrapped_key.lastMod.strftime("%Y-%m-%d %H:%M:%S") if wrapped_key.lastMod is not None else '--',
    'ext':wrapped_key.extension if wrapped_key.extension is not None else '--',
    'uploadUrl': key_upload_path(wrapped_key,url),
    'downloadUrl':url + URLADDONS['download'],
    'deleteUrl':url + URLADDONS['delete'],
	}	

def key_upload_path(wrapped_key,url):
    #TODO clean up url replacement etc
    #TODO use urllib
    if wrapped_key.type != 'folder':
        return quote(url + URLADDONS['upload'])
    else:
        return quote(url + URLADDONS['upload'] + wrapped_key.fullPath + '/')