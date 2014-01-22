from api import S3Wrapper,S3Key
from urllib import quote
from boto.s3.cors import CORSConfiguration


URLADDONS = {
        'delete':'delete/',
        'upload':'upload/',
        'download':'download/',
}

#This is for adjusting the cors of an s3 bucket, not used during development
ALLOWED_ORIGIN = "osf.io"

CORS_RULE = '<CORSRule><AllowedMethod>POST</AllowedMethod><AllowedOrigin>*</AllowedOrigin><AllowedHeader>origin</AllowedHeader><AllowedHeader>Content-Type</AllowedHeader><AllowedHeader>x-amz-acl</AllowedHeader><AllowedHeader>Authorization</AllowedHeader></CORSRule>'

#TODO fix/figure out allowed origin....
def adjust_cors(s3wrapper):
    rules = s3wrapper.get_cors_rules()
    if not [rule for rule in rules if rule.to_xml() == CORS_RULE]:
        rules.add_rule('PUT','*',allowed_header={'Authorization','Content-Type','x-amz-acl','origin'})
        print rules
        s3wrapper.set_cors_rules(rules)

def getHgrid(url,s3wrapper):
    keyList = s3wrapper.get_wrapped_keys()
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
    checkFolders(s3wrapper,keyList)
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
        if k.parentFolder is not None and k.parentFolder not in [x.name for x in keyList]:
        	newKey = s3wrapper.create_folder(k.pathTo)
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