list_file = {
    'etag':'"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MrSD7Al_zGPN4CKisJpWLDC3cyY"',
    'kind':'drive#fileList',
    'items': [
        {
            'etag':'"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQyMDEzMTI5ODkyOQ"',
            'owners':[
                {
                    'picture':{
                        'url':'https://lh3.googleusercontent.com/-ndG-yHyqonM/AAAAAAAAAAI/AAAAAAAAADs/wUR8YhDe3vY/s64/photo.jpg'
                    },
                    'kind':'drive#user',
                    'permissionId':'07992110234966807597',
                    'displayName':'Joshua Carp',
                    'emailAddress':'jm.carp@gmail.com',
                    'isAuthenticatedUser':True
                }
            ],
            'parents':[
                {
                    'parentLink':'https://www.googleapis.com/drive/v2/files/0ABtc_QrXguAwUk9PVA',
                    'isRoot':True,
                    'kind':'drive#parentReference',
                    'id':'0ABtc_QrXguAwUk9PVA',
                    'selfLink':'https://www.googleapis.com/drive/v2/files/1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR/parents/0ABtc_QrXguAwUk9PVA'
                }
            ],
            'ownerNames':[
                'Joshua Carp'
            ],
            'downloadUrl':'https://doc-0g-5k-docs.googleusercontent.com/docs/securesc/6l6ti67c1gnej8b4rr55nfimce1282lr/0sr833dlhh6p7ukpt3f4940se41ornad/1424880000000/07992110234966807597/07992110234966807597/1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR?e=download&gd=true',
            'writersCanShare':True,
            'title':'PART_1420130849837.pdf',
            'editable':True,
            'lastModifyingUser':{
                'picture':{
                    'url':'https://lh3.googleusercontent.com/-ndG-yHyqonM/AAAAAAAAAAI/AAAAAAAAADs/wUR8YhDe3vY/s64/photo.jpg'
                },
                'kind':'drive#user',
                'permissionId':'07992110234966807597',
                'displayName':'Joshua Carp',
                'emailAddress':'jm.carp@gmail.com',
                'isAuthenticatedUser':True
            },
            'quotaBytesUsed':'918668',
            'mimeType':'application/pdf',
            'createdDate':'2015-01-01T16:54:58.929Z',
            'alternateLink':'https://docs.google.com/file/d/1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR/edit?usp=drivesdk',
            'headRevisionId':'1DVR6FVQGOSpUrtHjxCKb4-2R0chGVJFG6wVPQwq1o-gay_tqwA',
            'id':'1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR',
            'modifiedDate':'2015-01-01T16:54:58.929Z',
            'kind':'drive#file',
            'fileExtension':'pdf',
            'iconLink':'https://ssl.gstatic.com/docs/doclist/images/icon_11_pdf_list.png',
            'appDataContents':False,
            'lastModifyingUserName':'Joshua Carp',
            'webContentLink':'https://docs.google.com/uc?id=1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR&export=download',
            'selfLink':'https://www.googleapis.com/drive/v2/files/1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR',
            'copyable':True,
            'fileSize':'918668',
            'labels':{
                'viewed':False,
                'trashed':False,
                'restricted':False,
                'hidden':False,
                'starred':False
            },
            'version':'143933',
            'md5Checksum':'43c5a01efeaea6bfd0433fa516a0d71f',
            'userPermission':{
                'type':'user',
                'kind':'drive#permission',
                'etag':'"zWM2D6PBtLRQKuDNbaQNSNEy5BE/2RVviHZ60Y5d9plBp5dBdmj2r70"',
                'id':'me',
                'selfLink':'https://www.googleapis.com/drive/v2/files/1GwpK7IozbO01RiyC5aPd66v7ShEViqggvT6ur5_pZMFo-ZzQHOgkyoU3ztjf0ytKt0HSdvUg6O2nmoYR/permissions/me',
                'role':'owner'
            },
            'shared':False,
            'markedViewedByMeDate':'1970-01-01T00:00:00.000Z'
        }
    ],
    'selfLink':"https://www.googleapis.com/drive/v2/files?q='0ABtc_QrXguAwUk9PVA'+in+parents+and+trashed+%3D+false+and+title+%3D+'PART_1420130849837.pdf'&alt=json"
}


list_file_empty = {
    'etag':'"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MrSD7Al_zGPN4CKisJpWLDC3cyY"',
    'kind':'drive#fileList',
    'items': [],
    'selfLink':"https://www.googleapis.com/drive/v2/files?q='0ABtc_QrXguAwUk9PVA'+in+parents+and+trashed+%3D+false+and+title+%3D+'PART_1420130849837.pdf'&alt=json"
}


def generate_list(child_id, **kwargs):
    item = {}
    item.update(list_file['items'][0])
    item.update(kwargs)
    item['id'] = child_id
    return {'items': [item]}
