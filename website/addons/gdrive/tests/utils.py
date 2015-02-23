# -*- coding: utf-8 -*-
import website


app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

mock_files_folders = {
 "kind": "drive#fileList",
 "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/OFY_BAPrn0m2U6l6Y1Al8txPdxM\"",
 "selfLink": "https://www.googleapis.com/drive/v2/files?q='0B8IkoNBph4qJenVUSDAxRFdjY1k'+in+parents+and+trashed%3DFalse",
 "items": [
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJbDV4cmpEM182RFk",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzU3ODcxNw\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJbDV4cmpEM182RFk",
   "webContentLink": "https://docs.google.com/uc?id=0B8IkoNBph4qJbDV4cmpEM182RFk&export=download",
   "alternateLink": "https://docs.google.com/file/d/0B8IkoNBph4qJbDV4cmpEM182RFk/edit?usp=drivesdk",
   "openWithLinks": {
    "457660898219": "https://accounts.google.com/o/oauth2/auth?scope=https://www.googleapis.com/auth/drive.file+https://www.googleapis.com/auth/drive+https://www.googleapis.com/auth/userinfo.email+https://www.googleapis.com/auth/userinfo.profile+https://docs.google.com/feeds/+https://docs.googleusercontent.com/feeds/&client_id=457660898219-m490arfh0gaim2bvsot4dg2jic6tvuos.apps.googleusercontent.com&response_type=code&access_type=offline&redirect_uri=https://gadgets.zoho.com/gdrive/writer&user_id=111890625752680749576&state=%7B%22ids%22:%5B%220B8IkoNBph4qJbDV4cmpEM182RFk%22%5D,%22action%22:%22open%22,%22userId%22:%22111890625752680749576%22%7D"
   },
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_10_text_list.png",
   "thumbnailLink": "https://lh3.googleusercontent.com/pRKEtkdSgQbmSctvtBx07GO2g2lHFbjNw0sCBvIdyUEwTiTGXNm998qWJzOz1sIW60AaaA=s220",
   "title": "Torrent downloaded from Demonoid.txt",
   "mimeType": "text/plain",
   "labels": {
    "starred": False,
    "hidden": True,
    "trashed": False,
    "restricted": False,
    "viewed": False
   },
   "createdDate": "2014-09-27T22:39:38.717Z",
   "modifiedDate": "2014-09-27T22:39:38.717Z",
   "modifiedByMeDate": "2014-09-27T22:39:38.717Z",
   "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
   "version": "14879",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJbDV4cmpEM182RFk/parents/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "isRoot": False
    }
   ],
   "downloadUrl": "https://doc-0o-4s-docs.googleusercontent.com/docs/securesc/tujj9q5cg2f1cm3jop9gn86ej796p8ll/0fnlldf3r65apevhqo7155ms5gtpes1c/1424037600000/03716493619382043449/03716493619382043449/0B8IkoNBph4qJbDV4cmpEM182RFk?e=download&gd=True",
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/IENhEp7JUQKowCOddON_fpygwuk\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJbDV4cmpEM182RFk/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "originalFilename": "Torrent downloaded from Demonoid.txt",
   "fileExtension": "txt",
   "md5Checksum": "0ba9b8b077f34d011dbe5bf4892a3cfe",
   "fileSize": "46",
   "quotaBytesUsed": "46",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": True,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False,
   "headRevisionId": "0B8IkoNBph4qJOE5kdGhyenlZMmxIVEoyNnRrNTViVUJkSm4wPQ"
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJRUNmVy12QWFnQWc",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzU3Nzg4NQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRUNmVy12QWFnQWc",
   "webContentLink": "https://docs.google.com/uc?id=0B8IkoNBph4qJRUNmVy12QWFnQWc&export=download",
   "alternateLink": "https://docs.google.com/file/d/0B8IkoNBph4qJRUNmVy12QWFnQWc/edit?usp=drivesdk",
   "openWithLinks": {
    "457660898219": "https://accounts.google.com/o/oauth2/auth?scope=https://www.googleapis.com/auth/drive.file+https://www.googleapis.com/auth/drive+https://www.googleapis.com/auth/userinfo.email+https://www.googleapis.com/auth/userinfo.profile+https://docs.google.com/feeds/+https://docs.googleusercontent.com/feeds/&client_id=457660898219-m490arfh0gaim2bvsot4dg2jic6tvuos.apps.googleusercontent.com&response_type=code&access_type=offline&redirect_uri=https://gadgets.zoho.com/gdrive/writer&user_id=111890625752680749576&state=%7B%22ids%22:%5B%220B8IkoNBph4qJRUNmVy12QWFnQWc%22%5D,%22action%22:%22open%22,%22userId%22:%22111890625752680749576%22%7D"
   },
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_10_text_list.png",
   "thumbnailLink": "https://lh4.googleusercontent.com/_iZdicljCKzylIT87wBiOTlCZcnuKXzCu3zNejKowi1XbqSok0ojCf5a2eBhpEADOCwYuA=s220",
   "title": "Torrent downloaded from AhaShare.com.txt",
   "mimeType": "text/plain",
   "labels": {
    "starred": False,
    "hidden": True,
    "trashed": False,
    "restricted": False,
    "viewed": False
   },
   "createdDate": "2014-09-27T22:39:37.885Z",
   "modifiedDate": "2014-09-27T22:39:37.885Z",
   "modifiedByMeDate": "2014-09-27T22:39:37.885Z",
   "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
   "version": "14880",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRUNmVy12QWFnQWc/parents/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "isRoot": False
    }
   ],
   "downloadUrl": "https://doc-10-4s-docs.googleusercontent.com/docs/securesc/tujj9q5cg2f1cm3jop9gn86ej796p8ll/ojj7q9f2h03ivo4sk5nckm19mkfcsggq/1424037600000/03716493619382043449/03716493619382043449/0B8IkoNBph4qJRUNmVy12QWFnQWc?e=download&gd=True",
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/j5r-DCqnrKy1l72lZhkDDLwyoUQ\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRUNmVy12QWFnQWc/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "originalFilename": "Torrent downloaded from AhaShare.com.txt",
   "fileExtension": "txt",
   "md5Checksum": "55e565dd59a868ba9d0366602e14c97b",
   "fileSize": "59",
   "quotaBytesUsed": "59",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": True,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False,
   "headRevisionId": "0B8IkoNBph4qJTi9KU0hyN2R3eEdRMzVMY05PQitTTUdTVklrPQ"
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJUjREMFF0bEFQTlk",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzU3Njg1Nw\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUjREMFF0bEFQTlk",
   "webContentLink": "https://docs.google.com/uc?id=0B8IkoNBph4qJUjREMFF0bEFQTlk&export=download",
   "alternateLink": "https://docs.google.com/file/d/0B8IkoNBph4qJUjREMFF0bEFQTlk/edit?usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_image_list.png",
   "thumbnailLink": "https://lh5.googleusercontent.com/kSJ3Pdm2QNQ2-shVblA1Ea9MVSSyd3ev_CHEvN_MYouxkAjVnxUfZJkazbUZc6-DUV_log=s220",
   "title": "Mantesh.jpg",
   "mimeType": "image/jpeg",
   "labels": {
    "starred": False,
    "hidden": True,
    "trashed": False,
    "restricted": False,
    "viewed": False
   },
   "createdDate": "2014-09-27T22:39:36.857Z",
   "modifiedDate": "2014-09-27T22:39:36.857Z",
   "modifiedByMeDate": "2014-09-27T22:39:36.857Z",
   "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
   "version": "14874",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUjREMFF0bEFQTlk/parents/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "isRoot": False
    }
   ],
   "downloadUrl": "https://doc-10-4s-docs.googleusercontent.com/docs/securesc/tujj9q5cg2f1cm3jop9gn86ej796p8ll/21u4h1e2lhoae5aoq7n4eo12vses1r7q/1424037600000/03716493619382043449/03716493619382043449/0B8IkoNBph4qJUjREMFF0bEFQTlk?e=download&gd=True",
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/w5nFwKOc3QNnwY4M_3kodROXJzo\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUjREMFF0bEFQTlk/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "originalFilename": "Mantesh.jpg",
   "fileExtension": "jpg",
   "md5Checksum": "0c3a38836f4e1e4dcd96bfc8e6d0e9fb",
   "fileSize": "75974",
   "quotaBytesUsed": "75974",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": True,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False,
   "headRevisionId": "0B8IkoNBph4qJcVJ6bHh6OERDMXpFanE2SVJ2NWJFaWFSa0RzPQ",
   "imageMediaMetadata": {
    "width": 400,
    "height": 606
   }
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJSVpjZ1FJUTJ5RTA",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzU3NjAwNQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA",
   "webContentLink": "https://docs.google.com/uc?id=0B8IkoNBph4qJSVpjZ1FJUTJ5RTA&export=download",
   "alternateLink": "https://docs.google.com/file/d/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA/edit?usp=drivesdk",
   "openWithLinks": {
    "1031094922298": "http://www.luminpdf.com/open/?state=%7B%22ids%22:%5B%220B8IkoNBph4qJSVpjZ1FJUTJ5RTA%22%5D,%22action%22:%22open%22,%22userId%22:%22111890625752680749576%22%7D"
   },
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_10_pdf_list.png",
   "thumbnailLink": "https://lh3.googleusercontent.com/Y8z38ZIt2zPAhaoBHKyi8Z0r1cMBVBZJ0FHBCLa96h2KcqBrEWSw4Tu7z8SA33CW0vWNPg=s220",
   "title": "Cracking the Coding Interview, 4 Edition - 150 Programming Interview Questions and Solutions.pdf",
   "mimeType": "application/pdf",
   "labels": {
    "starred": False,
    "hidden": True,
    "trashed": False,
    "restricted": False,
    "viewed": False
   },
   "createdDate": "2014-09-27T22:39:36.005Z",
   "modifiedDate": "2014-09-27T22:39:36.005Z",
   "modifiedByMeDate": "2014-09-27T22:39:36.005Z",
   "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
   "version": "14873",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA/parents/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k",
     "isRoot": False
    }
   ],
   "downloadUrl": "https://doc-08-4s-docs.googleusercontent.com/docs/securesc/tujj9q5cg2f1cm3jop9gn86ej796p8ll/fsmj9tb67k3alt8f4i9mm9naherhc4op/1424037600000/03716493619382043449/03716493619382043449/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA?e=download&gd=True",
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/-IguKToYlivdPOKVLm8-F-lrp4o\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "originalFilename": "Cracking the Coding Interview, 4 Edition - 150 Programming Interview Questions and Solutions.pdf",
   "fileExtension": "pdf",
   "md5Checksum": "4a77b3d15c6820472a3a2c7fb8f02426",
   "fileSize": "4048243",
   "quotaBytesUsed": "4048243",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": True,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False,
   "headRevisionId": "0B8IkoNBph4qJd2RMcng2TVBuZWZTRy8rdHpHUmc4dS81VTE4PQ"
  }
 ]
}


mock_folders = {

         "kind": "drive#fileList",
         "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/U8RO9tOkTpY5n55eC_2h11phZ30\"",
         "selfLink": "https://www.googleapis.com/drive/v2/files?q='0B8IkoNBph4qJeWlDanNYbm9LT2c'+in+parents+and+trashed%3DFalse+and+mimeType%3D%22application/vnd.google-apps.folder%22",
         "items": [
          {

           "kind": "drive#file",
           "id": "0B8IkoNBph4qJeU9OSWQtaUNwbFE",
           "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
           "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE",
           "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJeU9OSWQtaUNwbFE&usp=drivesdk",
           "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
           "title": "Portfolio",
           "mimeType": "application/vnd.google-apps.folder",
           "labels": {
            "starred": False,
            "hidden": False,
            "trashed": False,
            "restricted": False,
            "viewed": True
           },
           "createdDate": "2014-09-27T22:35:51.760Z",
           "modifiedDate": "2014-09-27T22:35:51.760Z",
           "lastViewedByMeDate": "2014-11-19T06:00:42.553Z",
           "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
           "version": "16982",
           "parents": [
            {

             "kind": "drive#parentReference",
             "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "isRoot": False
            }
           ],
           "userPermission": {
            "kind": "drive#permission",
            "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/t67v37TpTJx78_ogH-jpDny1NB0\"",
            "id": "me",
            "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE/permissions/me",
            "role": "owner",
            "type": "user"
           },
           "quotaBytesUsed": "0",
           "ownerNames": [
            "Kushagra Gupta"
           ],
           "owners": [
            {
             "kind": "drive#user",
             "displayName": "Kushagra Gupta",
             "picture": {
              "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
             },
             "isAuthenticatedUser": True,
             "permissionId": "03716493619382043449",
             "emailAddress": "imkushagra@gmail.com"
            }
           ],
           "lastModifyingUserName": "Kushagra Gupta",
           "lastModifyingUser": {
            "kind": "drive#user",
            "displayName": "Kushagra Gupta",
            "picture": {
             "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
            },
            "isAuthenticatedUser": True,
            "permissionId": "03716493619382043449",
            "emailAddress": "imkushagra@gmail.com"
           },
           "editable": True,
           "copyable": False,
           "writersCanShare": True,
           "shared": False,
           "appDataContents": False
          },
          {

           "kind": "drive#file",
           "id": "0B8IkoNBph4qJZ0hORDNsbHJJSzQ",
           "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
           "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ",
           "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZ0hORDNsbHJJSzQ&usp=drivesdk",
           "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
           "title": "Resume",
           "mimeType": "application/vnd.google-apps.folder",
           "labels": {
            "starred": False,
            "hidden": False,
            "trashed": False,
            "restricted": False,
            "viewed": True
           },
           "createdDate": "2014-09-27T22:35:51.760Z",
           "modifiedDate": "2014-09-27T22:35:51.760Z",
           "lastViewedByMeDate": "2014-11-19T06:00:48.027Z",
           "markedViewedByMeDate": "2014-09-27T22:55:27.484Z",
           "version": "16983",
           "parents": [
            {

             "kind": "drive#parentReference",
             "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "isRoot": False
            }
           ],
           "userPermission": {
            "kind": "drive#permission",
            "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/YXBw3kpw0bgZ4tLR0hdd0JH-BlY\"",
            "id": "me",
            "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ/permissions/me",
            "role": "owner",
            "type": "user"
           },
           "quotaBytesUsed": "0",
           "ownerNames": [
            "Kushagra Gupta"
           ],
           "owners": [
            {
             "kind": "drive#user",
             "displayName": "Kushagra Gupta",
             "picture": {
              "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
             },
             "isAuthenticatedUser": True,
             "permissionId": "03716493619382043449",
             "emailAddress": "imkushagra@gmail.com"
            }
           ],
           "lastModifyingUserName": "Kushagra Gupta",
           "lastModifyingUser": {
            "kind": "drive#user",
            "displayName": "Kushagra Gupta",
            "picture": {
             "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
            },
            "isAuthenticatedUser": True,
            "permissionId": "03716493619382043449",
            "emailAddress": "imkushagra@gmail.com"
           },
           "editable": True,
           "copyable": False,
           "writersCanShare": True,
           "shared": False,
           "appDataContents": False
          },
          {

           "kind": "drive#file",
           "id": "0B8IkoNBph4qJZmR5aUdSOEE3NGs",
           "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
           "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
           "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZmR5aUdSOEE3NGs&usp=drivesdk",
           "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
           "title": "Books",
           "mimeType": "application/vnd.google-apps.folder",
           "labels": {
            "starred": False,
            "hidden": False,
            "trashed": False,
            "restricted": False,
            "viewed": True
           },
           "createdDate": "2014-09-27T22:35:51.760Z",
           "modifiedDate": "2014-09-27T22:35:51.760Z",
           "lastViewedByMeDate": "2015-02-11T20:49:41.953Z",
           "markedViewedByMeDate": "2014-12-09T15:02:15.658Z",
           "version": "20900",
           "parents": [
            {

             "kind": "drive#parentReference",
             "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "isRoot": False
            }
           ],
           "userPermission": {
            "kind": "drive#permission",
            "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/wzYm9ul81FtNlP5K2MjdX4M4Z6k\"",
            "id": "me",
            "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs/permissions/me",
            "role": "owner",
            "type": "user"
           },
           "quotaBytesUsed": "0",
           "ownerNames": [
            "Kushagra Gupta"
           ],
           "owners": [
            {
             "kind": "drive#user",
             "displayName": "Kushagra Gupta",
             "picture": {
              "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
             },
             "isAuthenticatedUser": True,
             "permissionId": "03716493619382043449",
             "emailAddress": "imkushagra@gmail.com"
            }
           ],
           "lastModifyingUserName": "Kushagra Gupta",
           "lastModifyingUser": {
            "kind": "drive#user",
            "displayName": "Kushagra Gupta",
            "picture": {
             "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
            },
            "isAuthenticatedUser": True,
            "permissionId": "03716493619382043449",
            "emailAddress": "imkushagra@gmail.com"
           },
           "editable": True,
           "copyable": False,
           "writersCanShare": True,
           "shared": False,
           "appDataContents": False
          },
          {

           "kind": "drive#file",
           "id": "0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
           "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
           "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
           "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk",
           "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
           "title": "Cover Letters",
           "mimeType": "application/vnd.google-apps.folder",
           "labels": {
            "starred": False,
            "hidden": False,
            "trashed": False,
            "restricted": False,
            "viewed": True
           },
           "createdDate": "2014-09-27T22:35:51.760Z",
           "modifiedDate": "2014-09-27T22:35:51.760Z",
           "lastViewedByMeDate": "2014-10-03T15:09:47.550Z",
           "markedViewedByMeDate": "2014-10-03T15:09:45.880Z",
           "version": "15023",
           "parents": [
            {

             "kind": "drive#parentReference",
             "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "isRoot": False
            }
           ],
           "userPermission": {
            "kind": "drive#permission",
            "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/BUcqbw0gcvz6B3GMqvXvGvdGS-w\"",
            "id": "me",
            "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/permissions/me",
            "role": "owner",
            "type": "user"
           },
           "quotaBytesUsed": "0",
           "ownerNames": [
            "Kushagra Gupta"
           ],
           "owners": [
            {
             "kind": "drive#user",
             "displayName": "Kushagra Gupta",
             "picture": {
              "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
             },
             "isAuthenticatedUser": True,
             "permissionId": "03716493619382043449",
             "emailAddress": "imkushagra@gmail.com"
            }
           ],
           "lastModifyingUserName": "Kushagra Gupta",
           "lastModifyingUser": {
            "kind": "drive#user",
            "displayName": "Kushagra Gupta",
            "picture": {
             "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
            },
            "isAuthenticatedUser": True,
            "permissionId": "03716493619382043449",
            "emailAddress": "imkushagra@gmail.com"
           },
           "editable": True,
           "copyable": False,
           "writersCanShare": True,
           "shared": False,
           "appDataContents": False
          },
          {

           "kind": "drive#file",
           "id": "0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
           "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
           "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
           "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk",
           "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
           "title": "Cover Letters",
           "mimeType": "application/vnd.google-apps.folder",
           "labels": {
            "starred": False,
            "hidden": False,
            "trashed": False,
            "restricted": False,
            "viewed": True
           },
           "createdDate": "2014-09-27T22:35:51.760Z",
           "modifiedDate": "2014-09-27T22:35:51.760Z",
           "lastViewedByMeDate": "2014-10-03T15:09:47.550Z",
           "markedViewedByMeDate": "2014-10-03T15:09:45.880Z",
           "version": "15023",
           "parents": [
            {

             "kind": "drive#parentReference",
             "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
             "isRoot": False
            }
           ],
           "userPermission": {
            "kind": "drive#permission",
            "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/BUcqbw0gcvz6B3GMqvXvGvdGS-w\"",
            "id": "me",
            "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/permissions/me",
            "role": "owner",
            "type": "user"
           },
           "quotaBytesUsed": "0",
           "ownerNames": [
            "Kushagra Gupta"
           ],
           "owners": [
            {
             "kind": "drive#user",
             "displayName": "Kushagra Gupta",
             "picture": {
              "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
             },
             "isAuthenticatedUser": True,
             "permissionId": "03716493619382043449",
             "emailAddress": "imkushagra@gmail.com"
            }
           ],
           "lastModifyingUserName": "Kushagra Gupta",
           "lastModifyingUser": {
            "kind": "drive#user",
            "displayName": "Kushagra Gupta",
            "picture": {
             "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
            },
            "isAuthenticatedUser": True,
            "permissionId": "03716493619382043449",
            "emailAddress": "imkushagra@gmail.com"
           },
           "editable": True,
           "copyable": False,
           "writersCanShare": True,
           "shared": False,
           "appDataContents": False
          }
         ]
        }

mock_root_folders = {
 "kind": "drive#fileList",
 "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/8uR2e44OlkttLETnPe12RbBieXY\"",
 "selfLink": "https://www.googleapis.com/drive/v2/files?q=trashed%3DFalse+and+mimeType%3D'application/vnd.google-apps.folder'",
 "items": [
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxNzQxMDI0MzUwMQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
   "webViewLink": "https://bbdd96037ece2445fdea4be607098721910701c6.googledrive.com/host/0B8IkoNBph4qJZUViX241ZElCMG8/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZUViX241ZElCMG8&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Public",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-09T00:49:50.281Z",
   "modifiedDate": "2014-12-01T05:04:03.501Z",
   "modifiedByMeDate": "2014-12-01T05:04:03.501Z",
   "lastViewedByMeDate": "2015-02-10T18:56:54.433Z",
   "markedViewedByMeDate": "2014-12-12T21:28:11.642Z",
   "version": "20826",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/kmjw_Z1znm9oW6hGq2UNvnLDC-Q\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJRlltcThyQ2tqdVE",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxNzQxMDI0MzUwMQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRlltcThyQ2tqdVE",
   "webViewLink": "https://d7c92b972d893e03482edf5a2a8cddf38f365434.googledrive.com/host/0B8IkoNBph4qJRlltcThyQ2tqdVE/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJRlltcThyQ2tqdVE&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "2048 Scramble Latest",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-12-01T05:03:26.996Z",
   "modifiedDate": "2014-12-01T05:04:03.501Z",
   "modifiedByMeDate": "2014-12-01T05:04:03.501Z",
   "lastViewedByMeDate": "2015-02-10T20:36:38.980Z",
   "markedViewedByMeDate": "2014-12-01T05:04:05.209Z",
   "version": "20835",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRlltcThyQ2tqdVE/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/9_lNg95yseaAoLRBC2BARhAT-gM\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRlltcThyQ2tqdVE/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJUXJFemUzWnZqa3c",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMzgxODgzNjc5MQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUXJFemUzWnZqa3c",
   "webViewLink": "https://3b0a85d7691f3d3faa8a9933374d5d17e9eb0960.googledrive.com/host/0B8IkoNBph4qJUXJFemUzWnZqa3c/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJUXJFemUzWnZqa3c&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "2048 Scramble",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-20T15:27:16.791Z",
   "modifiedDate": "2014-10-20T15:27:16.791Z",
   "lastViewedByMeDate": "2015-02-10T18:56:46.397Z",
   "markedViewedByMeDate": "2014-12-12T21:28:21.672Z",
   "version": "20825",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUXJFemUzWnZqa3c/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/sMePGeebO5xrKOychfn0vwICgsY\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJUXJFemUzWnZqa3c/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJdEI3aFE1Q0VOZGM",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjk4NzA0NTA2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdEI3aFE1Q0VOZGM",
   "webViewLink": "https://9e85300c8fd328bdb5c418bcfb1d30f57c569dbf.googledrive.com/host/0B8IkoNBph4qJdEI3aFE1Q0VOZGM/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJdEI3aFE1Q0VOZGM&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Bull Shit 2.0",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-11T00:23:45.045Z",
   "modifiedDate": "2014-10-11T00:24:05.060Z",
   "modifiedByMeDate": "2014-10-11T00:24:05.060Z",
   "lastViewedByMeDate": "2014-10-11T00:44:58.712Z",
   "markedViewedByMeDate": "2014-10-11T00:26:56.895Z",
   "version": "15564",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdEI3aFE1Q0VOZGM/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/bNAw5veeD5hKEJlvgqCFVFOXfR8\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdEI3aFE1Q0VOZGM/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJdjF3X3JwN0FULWs",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjk4NjQxODM5NQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdjF3X3JwN0FULWs",
   "webViewLink": "https://28fcf424d5c6758c1445177231408fdba004ac52.googledrive.com/host/0B8IkoNBph4qJdjF3X3JwN0FULWs/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJdjF3X3JwN0FULWs&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Bull Shit OG",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-11T00:13:38.395Z",
   "modifiedDate": "2014-10-11T00:13:38.395Z",
   "lastViewedByMeDate": "2014-10-11T00:43:23.875Z",
   "markedViewedByMeDate": "2014-10-11T00:43:23.767Z",
   "version": "15561",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdjF3X3JwN0FULWs/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/lHDS1-kQ0_TREn-4q9UcDmo7_zs\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJdjF3X3JwN0FULWs/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJa0FXdEFjOUtxaGM",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjgxNzIwNDE0MQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJa0FXdEFjOUtxaGM",
   "webViewLink": "https://f352b1e47ebdd6d341da10a6750987da1b6d6a96.googledrive.com/host/0B8IkoNBph4qJa0FXdEFjOUtxaGM/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJa0FXdEFjOUtxaGM&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Time is of the Essence",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-09T01:13:24.141Z",
   "modifiedDate": "2014-10-09T01:13:24.141Z",
   "lastViewedByMeDate": "2015-02-10T01:33:55.038Z",
   "markedViewedByMeDate": "2014-10-09T01:13:29.042Z",
   "version": "20807",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJa0FXdEFjOUtxaGM/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/pzSVU8sfqoU7xxSQruQx_-6djGE\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJa0FXdEFjOUtxaGM/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJd25GRmplRE8tQmM",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjgxNzE5MjM3NA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJd25GRmplRE8tQmM",
   "webViewLink": "https://3069594c5ab7c04bc3d6d93cbf53824a16117798.googledrive.com/host/0B8IkoNBph4qJd25GRmplRE8tQmM/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJd25GRmplRE8tQmM&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Celestial Ladder",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-09T01:08:51.778Z",
   "modifiedDate": "2014-10-09T01:13:12.374Z",
   "modifiedByMeDate": "2014-10-09T01:13:12.374Z",
   "lastViewedByMeDate": "2014-10-10T04:04:04.748Z",
   "markedViewedByMeDate": "2014-10-10T04:04:10.842Z",
   "version": "15474",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZUViX241ZElCMG8",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJd25GRmplRE8tQmM/parents/0B8IkoNBph4qJZUViX241ZElCMG8",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZUViX241ZElCMG8",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/nQ-eWxv2mgT1WFkxlr-AwBHfdHQ\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJd25GRmplRE8tQmM/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJV3F3TTFiai1ZT2M",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjgxNTQzNDU0Mw\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJV3F3TTFiai1ZT2M",
   "webViewLink": "https://c99f331e1529eb073bc9e05258789a78f2e4f945.googledrive.com/host/0B8IkoNBph4qJV3F3TTFiai1ZT2M/",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJV3F3TTFiai1ZT2M&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Test Unity Web",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-08T23:20:24.147Z",
   "modifiedDate": "2014-10-09T00:43:54.543Z",
   "lastViewedByMeDate": "2014-10-08T23:20:28.961Z",
   "markedViewedByMeDate": "2014-10-08T23:20:29.104Z",
   "version": "15140",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJRW5wVzctSzRmdlk",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJV3F3TTFiai1ZT2M/parents/0B8IkoNBph4qJRW5wVzctSzRmdlk",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRW5wVzctSzRmdlk",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/_Vxv6-xKgkszEawVh0pdH3FKjKA\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJV3F3TTFiai1ZT2M/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJRW5wVzctSzRmdlk",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMjgxMDQyNDE0Nw\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRW5wVzctSzRmdlk",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJRW5wVzctSzRmdlk&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "myGames",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-10-08T23:20:24.147Z",
   "modifiedDate": "2014-10-08T23:20:24.147Z",
   "lastViewedByMeDate": "2015-02-11T20:29:23.107Z",
   "markedViewedByMeDate": "2015-02-04T18:59:43.738Z",
   "version": "20880",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRW5wVzctSzRmdlk/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/UJJrJdw690qJqLy1LDemFACIaBI\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJRW5wVzctSzRmdlk/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJenVUSDAxRFdjY1k",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJenVUSDAxRFdjY1k&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Cracking the Coding Interview 150 Programming Interview Questions and Solutions",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2015-02-11T20:21:26.803Z",
   "markedViewedByMeDate": "2015-02-05T04:22:49.252Z",
   "version": "20861",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k/parents/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/eh6r2G4xkGUDTYfB6q7pgu2BRU8\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJenVUSDAxRFdjY1k/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJeWlDanNYbm9LT2c&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Jobs",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2015-02-15T01:07:58.872Z",
   "markedViewedByMeDate": "2014-12-09T15:02:11.855Z",
   "version": "20983",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJYkJ4OHVqUnVHZFE",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c/parents/0B8IkoNBph4qJYkJ4OHVqUnVHZFE",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYkJ4OHVqUnVHZFE",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/TpcVIdjyymLv1XEoMuX-aadTfJU\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJeU9OSWQtaUNwbFE",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJeU9OSWQtaUNwbFE&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Portfolio",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2014-11-19T06:00:42.553Z",
   "markedViewedByMeDate": "1970-01-01T00:00:00.000Z",
   "version": "16982",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/t67v37TpTJx78_ogH-jpDny1NB0\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeU9OSWQtaUNwbFE/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJZ0hORDNsbHJJSzQ",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZ0hORDNsbHJJSzQ&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Resume",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2014-11-19T06:00:48.027Z",
   "markedViewedByMeDate": "2014-09-27T22:55:27.484Z",
   "version": "16983",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/YXBw3kpw0bgZ4tLR0hdd0JH-BlY\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZ0hORDNsbHJJSzQ/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJZmR5aUdSOEE3NGs",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZmR5aUdSOEE3NGs&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Books",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2015-02-11T20:49:41.953Z",
   "markedViewedByMeDate": "2014-12-09T15:02:15.658Z",
   "version": "20900",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/wzYm9ul81FtNlP5K2MjdX4M4Z6k\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Cover Letters",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2014-10-03T15:09:47.550Z",
   "markedViewedByMeDate": "2014-10-03T15:09:45.880Z",
   "version": "15023",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/parents/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJeWlDanNYbm9LT2c",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/BUcqbw0gcvz6B3GMqvXvGvdGS-w\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmRhRWg3Xy05MzQ/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJNi1TT0N1bC1fQzg",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NzM1MTc2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJNi1TT0N1bC1fQzg",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJNi1TT0N1bC1fQzg&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Interview",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:35:51.760Z",
   "modifiedDate": "2014-09-27T22:35:51.760Z",
   "lastViewedByMeDate": "2014-10-01T21:33:37.615Z",
   "markedViewedByMeDate": "2014-10-01T21:33:37.701Z",
   "version": "14995",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJNi1TT0N1bC1fQzg/parents/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZmR5aUdSOEE3NGs",
     "isRoot": False
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/DJP0-qL_woeDJ3JTxbhCcl6CUvs\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJNi1TT0N1bC1fQzg/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJYkJ4OHVqUnVHZFE",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQxMTg1NjY5MjI0MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYkJ4OHVqUnVHZFE",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJYkJ4OHVqUnVHZFE&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Jobs",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-09-27T22:24:52.240Z",
   "modifiedDate": "2014-09-27T22:24:52.240Z",
   "lastViewedByMeDate": "2015-02-15T01:07:57.439Z",
   "markedViewedByMeDate": "2014-12-09T15:02:10.595Z",
   "version": "20980",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYkJ4OHVqUnVHZFE/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/howkWIeLED_eVsPkIGfyMteBR5Y\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYkJ4OHVqUnVHZFE/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJZTRjQ3doVVgyd00",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTQwMDI2ODIyOTAwNQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZTRjQ3doVVgyd00",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJZTRjQ3doVVgyd00&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Audio",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-05-16T19:23:49.005Z",
   "modifiedDate": "2014-05-16T19:23:49.005Z",
   "lastViewedByMeDate": "2015-02-05T04:42:11.890Z",
   "markedViewedByMeDate": "2014-06-08T19:10:34.192Z",
   "version": "20672",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZTRjQ3doVVgyd00/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/oV0KQp3QUMssQkcwVLF2jPH0GUM\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJZTRjQ3doVVgyd00/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJTk9kdVY5TkFPUFE",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTM5OTkwMzA0MTM2MA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJTk9kdVY5TkFPUFE",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJTk9kdVY5TkFPUFE&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Networking",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-05-12T13:57:01.616Z",
   "modifiedDate": "2014-05-12T13:57:21.360Z",
   "modifiedByMeDate": "2014-05-12T13:57:21.360Z",
   "lastViewedByMeDate": "2015-02-07T00:02:51.465Z",
   "markedViewedByMeDate": "2014-05-12T14:00:47.853Z",
   "version": "20734",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJTk9kdVY5TkFPUFE/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/t9WYOCKCXgATEnxHalGCSujOTSU\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJTk9kdVY5TkFPUFE/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJYmZmdnlkOVZya2c",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTM5OTkwMzAwODA5MQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmZmdnlkOVZya2c",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJYmZmdnlkOVZya2c&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "GGP",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-04-04T17:28:17.504Z",
   "modifiedDate": "2014-05-12T13:56:48.091Z",
   "modifiedByMeDate": "2014-05-12T13:56:48.091Z",
   "lastViewedByMeDate": "2015-02-05T04:42:10.509Z",
   "markedViewedByMeDate": "2014-12-09T14:54:03.513Z",
   "version": "20670",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmZmdnlkOVZya2c/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/8cLEy9pBzolOGqrZaUc23Tjkshw\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJYmZmdnlkOVZya2c/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJWFRLSHltcmdHRDA",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTM5NjI4MTM5MDE1NA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJWFRLSHltcmdHRDA",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJWFRLSHltcmdHRDA&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "sayname",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2014-03-31T15:56:30.154Z",
   "modifiedDate": "2014-03-31T15:56:30.154Z",
   "lastViewedByMeDate": "2015-02-10T01:37:17.695Z",
   "markedViewedByMeDate": "2014-03-31T16:04:10.195Z",
   "version": "20814",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJWFRLSHltcmdHRDA/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/v80fVSMQmUMH6oETQT1doHPqlLk\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJWFRLSHltcmdHRDA/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0B8IkoNBph4qJb1F2S3RQRVl0UzQ",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTM4ODgwNDYxMDc3OA\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJb1F2S3RQRVl0UzQ",
   "alternateLink": "https://docs.google.com/folderview?id=0B8IkoNBph4qJb1F2S3RQRVl0UzQ&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "mYgAmes",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2013-12-29T22:28:42.365Z",
   "modifiedDate": "2014-01-04T03:03:30.778Z",
   "modifiedByMeDate": "2014-01-04T03:03:30.778Z",
   "lastViewedByMeDate": "2015-02-05T04:42:08.315Z",
   "markedViewedByMeDate": "2014-12-09T15:01:02.632Z",
   "version": "20668",
   "parents": [
    {

     "kind": "drive#parentReference",
     "id": "0AMIkoNBph4qJUk9PVA",
     "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJb1F2S3RQRVl0UzQ/parents/0AMIkoNBph4qJUk9PVA",
     "parentLink": "https://www.googleapis.com/drive/v2/files/0AMIkoNBph4qJUk9PVA",
     "isRoot": True
    }
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/HH-QLdDf9gnoAHzkGEoed1_dDRs\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0B8IkoNBph4qJb1F2S3RQRVl0UzQ/permissions/me",
    "role": "owner",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Kushagra Gupta"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Kushagra Gupta",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
     },
     "isAuthenticatedUser": True,
     "permissionId": "03716493619382043449",
     "emailAddress": "imkushagra@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": False,
   "appDataContents": False
  },
  {

   "kind": "drive#file",
   "id": "0Bx_h7N2n3_3VZE5RZXJGTDIyVnc",
   "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/MTM4MTg3ODIzNTIwMQ\"",
   "selfLink": "https://www.googleapis.com/drive/v2/files/0Bx_h7N2n3_3VZE5RZXJGTDIyVnc",
   "alternateLink": "https://docs.google.com/folderview?id=0Bx_h7N2n3_3VZE5RZXJGTDIyVnc&usp=drivesdk",
   "iconLink": "https://ssl.gstatic.com/docs/doclist/images/icon_11_collection_list.png",
   "title": "Conqueror of Kingdoms",
   "mimeType": "application/vnd.google-apps.folder",
   "labels": {
    "starred": False,
    "hidden": False,
    "trashed": False,
    "restricted": False,
    "viewed": True
   },
   "createdDate": "2013-09-27T01:06:01.911Z",
   "modifiedDate": "2013-10-15T23:03:55.201Z",
   "modifiedByMeDate": "2013-10-15T23:03:55.201Z",
   "lastViewedByMeDate": "2014-03-15T19:33:16.416Z",
   "markedViewedByMeDate": "2014-03-15T19:33:16.495Z",
   "sharedWithMeDate": "2013-09-27T01:07:42.816Z",
   "version": "13537",
   "sharingUser": {
    "kind": "drive#user",
    "displayName": "Rushabh Gosar",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-ZvzdgXa1w9o/AAAAAAAAAAI/AAAAAAAAIJw/3Q5za_0T_1Q/s64/photo.jpg"
    },
    "isAuthenticatedUser": False,
    "permissionId": "08913471013364666999",
    "emailAddress": "rushabh.techie@gmail.com"
   },
   "parents": [
   ],
   "userPermission": {
    "kind": "drive#permission",
    "etag": "\"zWM2D6PBtLRQKuDNbaQNSNEy5BE/24y2r0v9zEJPfjgajp3-WZ34x9Y\"",
    "id": "me",
    "selfLink": "https://www.googleapis.com/drive/v2/files/0Bx_h7N2n3_3VZE5RZXJGTDIyVnc/permissions/me",
    "role": "writer",
    "type": "user"
   },
   "quotaBytesUsed": "0",
   "ownerNames": [
    "Rushabh Gosar"
   ],
   "owners": [
    {
     "kind": "drive#user",
     "displayName": "Rushabh Gosar",
     "picture": {
      "url": "https://lh4.googleusercontent.com/-ZvzdgXa1w9o/AAAAAAAAAAI/AAAAAAAAIJw/3Q5za_0T_1Q/s64/photo.jpg"
     },
     "isAuthenticatedUser": False,
     "permissionId": "08913471013364666999",
     "emailAddress": "rushabh.techie@gmail.com"
    }
   ],
   "lastModifyingUserName": "Kushagra Gupta",
   "lastModifyingUser": {
    "kind": "drive#user",
    "displayName": "Kushagra Gupta",
    "picture": {
     "url": "https://lh4.googleusercontent.com/-kZ7H558nSOU/AAAAAAAAAAI/AAAAAAAAAJY/t1Cv0o4T-Lw/s64/photo.jpg"
    },
    "isAuthenticatedUser": True,
    "permissionId": "03716493619382043449",
    "emailAddress": "imkushagra@gmail.com"
   },
   "editable": True,
   "copyable": False,
   "writersCanShare": True,
   "shared": True,
   "appDataContents": False
  }
 ]
}

def create_mock_dict(mock_dict):
    mock_dict.__getitem__.side_effect = getitem
    mock_dict.__setitem__.side_effect = setitem


def getitem(key):
    return mock_folders[key]


def setitem(key, val):
     mock_folders[key] = val