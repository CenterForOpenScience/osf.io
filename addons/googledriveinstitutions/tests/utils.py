# -*- coding: utf-8 -*-

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.googledriveinstitutions.models import GoogleDriveInstitutionsProvider
from addons.googledriveinstitutions.tests.factories import GoogleDriveInstitutionsAccountFactory

class GoogleDriveInstitutionsAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'googledriveinstitutions'
    ExternalAccountFactory = GoogleDriveInstitutionsAccountFactory
    Provider = GoogleDriveInstitutionsProvider

    def set_node_settings(self, settings):
        super(GoogleDriveInstitutionsAddonTestCase, self).set_node_settings(settings)
        settings.folder_id = '1234567890'
        settings.folder_path = 'Drive/Camera Uploads'
        settings.external_account = self.external_account
        settings.save()

mock_files_folders = {

 'kind': 'drive#fileList',
 'files': [
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJbDV4cmpEM182RFk',
   'name': 'Torrent downloaded from Demonoid.txt',
   'mimeType': 'text/plain',
   'trashed': False,
   'parents': [
     '0B8IkoNBph4qJenVUSDAxRFdjY1k'
   ],
   'version': '14879',
   "webViewLink": "https://docs.google.com/file/d/0B8IkoNBph4qJbDV4cmpEM182RFk/edit?usp=drivesdk",
   'createdTime': '2014-09-27T22:39:38.717Z',
   'modifiedTime': '2014-09-27T22:39:38.717Z',
   "capabilities": {
    "canEdit": True
   },
   'originalFilename': 'Torrent downloaded from Demonoid.txt',
   'md5Checksum': '0ba9b8b077f34d011dbe5bf4892a3cfe',
   'size': '46'
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJRUNmVy12QWFnQWc',
   'name': 'Torrent downloaded from AhaShare.com.txt',
   'mimeType': 'text/plain',
   'trashed': False,
   'parents': [
     '0B8IkoNBph4qJenVUSDAxRFdjY1k',
   ],
   'version': '14880',
   'webViewLink': 'https://docs.google.com/file/d/0B8IkoNBph4qJRUNmVy12QWFnQWc/edit?usp=drivesdk',
   'createdTime': '2014-09-27T22:39:37.885Z',
   'modifiedTime': '2014-09-27T22:39:37.885Z',
   "capabilities": {
    "canEdit": True
   },
   'originalFilename': 'Torrent downloaded from AhaShare.com.txt',
   'md5Checksum': '55e565dd59a868ba9d0366602e14c97b',
   'size': '59'
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJUjREMFF0bEFQTlk',
   'name': 'Mantesh.jpg',
   'mimeType': 'image/jpeg',
   'trashed': False,
   'parents': [
     '0B8IkoNBph4qJenVUSDAxRFdjY1k',
   ],
   'version': '14874',
   'webViewLink': 'https://docs.google.com/file/d/0B8IkoNBph4qJUjREMFF0bEFQTlk/edit?usp=drivesdk',
   'createdTime': '2014-09-27T22:39:36.857Z',
   'modifiedTime': '2014-09-27T22:39:36.857Z',
   "capabilities": {
    "canEdit": True
   },
   'originalFilename': 'Mantesh.jpg',
   'md5Checksum': '0c3a38836f4e1e4dcd96bfc8e6d0e9fb',
   'size': '75974'
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJSVpjZ1FJUTJ5RTA',
   'name': 'Cracking the Coding Interview, 4 Edition - 150 Programming Interview Questions and Solutions.pdf',
   'mimeType': 'application/pdf',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJenVUSDAxRFdjY1k'
   ],
   'version': '14873',
   'webViewLink': 'https://docs.google.com/file/d/0B8IkoNBph4qJSVpjZ1FJUTJ5RTA/edit?usp=drivesdk',
   'createdTime': '2014-09-27T22:39:36.005Z',
   'modifiedTime': '2014-09-27T22:39:36.005Z',
   "capabilities": {
    "canEdit": True
   },
   'originalFilename': 'Cracking the Coding Interview, 4 Edition - 150 Programming Interview Questions and Solutions.pdf',
   'md5Checksum': '4a77b3d15c6820472a3a2c7fb8f02426',
   'size': '4048243'
  }
 ]
}


mock_folders = {

         'kind': 'drive#fileList',
         'files': [
          {

           'kind': 'drive#file',
           'id': '0B8IkoNBph4qJeU9OSWQtaUNwbFE',
           'name': u'Новая папка',  # Google drive actually sends back in unicode, this will work without the u".."
           'mimeType': 'application/vnd.google-apps.folder',
           'trashed': False,
           'parents': [
               '0B8IkoNBph4qJeWlDanNYbm9LT2c'
           ],
           'version': '16982',
           'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJeU9OSWQtaUNwbFE&usp=drivesdk',
           'createdTime': '2014-09-27T22:35:51.760Z',
           'modifiedTime': '2014-09-27T22:35:51.760Z',
           "capabilities": {
               "canEdit": True
           }
          },
          {

           'kind': 'drive#file',
           'id': '0B8IkoNBph4qJZ0hORDNsbHJJSzQ',
           'name': 'Resume',
           'mimeType': 'application/vnd.google-apps.folder',
           'trashed': False,
           'parents': [
               '0B8IkoNBph4qJeWlDanNYbm9LT2c'
           ],
           'version': '16983',
           'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZ0hORDNsbHJJSzQ&usp=drivesdk',
           'createdTime': '2014-09-27T22:35:51.760Z',
           'modifiedTime': '2014-09-27T22:35:51.760Z',
           "capabilities": {
               "canEdit": True
           }
          },
          {

           'kind': 'drive#file',
           'id': '0B8IkoNBph4qJZmR5aUdSOEE3NGs',
           'name': 'Books',
           'mimeType': 'application/vnd.google-apps.folder',
           'trashed': False,
           'parents': [
               '0B8IkoNBph4qJeWlDanNYbm9LT2c'
           ],
           'version': '20900',
           'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZmR5aUdSOEE3NGs&usp=drivesdk',
           'createdTime': '2014-09-27T22:35:51.760Z',
           'modifiedTime': '2014-09-27T22:35:51.760Z',
           "capabilities": {
               "canEdit": True
           }
          },
          {

           'kind': 'drive#file',
           'id': '0B8IkoNBph4qJYmRhRWg3Xy05MzQ',
           'name': 'Cover Letters',
           'mimeType': 'application/vnd.google-apps.folder',
           'trashed': False,
           'parents': [
               '0B8IkoNBph4qJeWlDanNYbm9LT2c'
           ],
           'version': '15023',
           'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk',
           'createdTime': '2014-09-27T22:35:51.760Z',
           'modifiedTime': '2014-09-27T22:35:51.760Z',
           "capabilities": {
               "canEdit": True
           }
          },
          {

           'kind': 'drive#file',
           'id': '0B8IkoNBph4qJYmRhRWg3Xy05MzQ',
           'name': 'Cover Letters',
           'mimeType': 'application/vnd.google-apps.folder',
           'trashed': False,
           'parents': [
               '0B8IkoNBph4qJeWlDanNYbm9LT2c'
           ],
           'version': '15023',
           'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk',
           'createdTime': '2014-09-27T22:35:51.760Z',
           'modifiedTime': '2014-09-27T22:35:51.760Z',
           "capabilities": {
               "canEdit": True
           }
          }
         ]
        }

mock_root_folders = {

 'kind': 'drive#fileList',
 'files': [
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJZUViX241ZElCMG8',
   'name': 'Public',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20826',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZUViX241ZElCMG8&usp=drivesdk',
   'createdTime': '2014-10-09T00:49:50.281Z',
   'modifiedTime': '2014-12-01T05:04:03.501Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJRlltcThyQ2tqdVE',
   'name': '2048 Scramble Latest',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '20835',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJRlltcThyQ2tqdVE&usp=drivesdk',
   'createdTime': '2014-12-01T05:03:26.996Z',
   'modifiedTime': '2014-12-01T05:04:03.501Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJUXJFemUzWnZqa3c',
   'name': '2048 Scramble',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '20825',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJUXJFemUzWnZqa3c&usp=drivesdk',
   'createdTime': '2014-10-20T15:27:16.791Z',
   'modifiedTime': '2014-10-20T15:27:16.791Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJdEI3aFE1Q0VOZGM',
   'name': 'Bull Shit 2.0',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '15564',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJdEI3aFE1Q0VOZGM&usp=drivesdk',
   'createdTime': '2014-10-11T00:23:45.045Z',
   'modifiedTime': '2014-10-11T00:24:05.060Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJdjF3X3JwN0FULWs',
   'name': 'Bull Shit OG',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '15561',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJdjF3X3JwN0FULWs&usp=drivesdk',
   'createdTime': '2014-10-11T00:13:38.395Z',
   'modifiedTime': '2014-10-11T00:13:38.395Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJa0FXdEFjOUtxaGM',
   'name': 'Time is of the Essence',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '20807',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJa0FXdEFjOUtxaGM&usp=drivesdk',
   'createdTime': '2014-10-09T01:13:24.141Z',
   'modifiedTime': '2014-10-09T01:13:24.141Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJd25GRmplRE8tQmM',
   'name': 'Celestial Ladder',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZUViX241ZElCMG8'
   ],
   'version': '15474',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJd25GRmplRE8tQmM&usp=drivesdk',
   'createdTime': '2014-10-09T01:08:51.778Z',
   'modifiedTime': '2014-10-09T01:13:12.374Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJV3F3TTFiai1ZT2M',
   'name': 'Test Unity Web',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJRW5wVzctSzRmdlk'
   ],
   'version': '15140',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJV3F3TTFiai1ZT2M&usp=drivesdk',
   'createdTime': '2014-10-08T23:20:24.147Z',
   'modifiedTime': '2014-10-09T00:43:54.543Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJRW5wVzctSzRmdlk',
   'name': 'myGames',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20880',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJRW5wVzctSzRmdlk&usp=drivesdk',
   'createdTime': '2014-10-08T23:20:24.147Z',
   'modifiedTime': '2014-10-08T23:20:24.147Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJenVUSDAxRFdjY1k',
   'name': 'Cracking the Coding Interview 150 Programming Interview Questions and Solutions',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZmR5aUdSOEE3NGs'
   ],
   'version': '20861',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJenVUSDAxRFdjY1k&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJeWlDanNYbm9LT2c',
   'name': 'Jobs',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJYkJ4OHVqUnVHZFE'
   ],
   'version': '20983',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJeWlDanNYbm9LT2c&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJeU9OSWQtaUNwbFE',
   'name': 'Portfolio',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJeWlDanNYbm9LT2c'
   ],
   'version': '16982',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJeU9OSWQtaUNwbFE&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJZ0hORDNsbHJJSzQ',
   'name': 'Resume',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJeWlDanNYbm9LT2c'
   ],
   'version': '16983',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZ0hORDNsbHJJSzQ&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJZmR5aUdSOEE3NGs',
   'name': 'Books',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJeWlDanNYbm9LT2c'
   ],
   'version': '20900',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZmR5aUdSOEE3NGs&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJYmRhRWg3Xy05MzQ',
   'name': 'Cover Letters',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJeWlDanNYbm9LT2c'
   ],
   'version': '15023',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJYmRhRWg3Xy05MzQ&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJNi1TT0N1bC1fQzg',
   'name': 'Interview',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0B8IkoNBph4qJZmR5aUdSOEE3NGs'
   ],
   'version': '14995',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJNi1TT0N1bC1fQzg&usp=drivesdk',
   'createdTime': '2014-09-27T22:35:51.760Z',
   'modifiedTime': '2014-09-27T22:35:51.760Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJYkJ4OHVqUnVHZFE',
   'name': 'Jobs',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20980',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJYkJ4OHVqUnVHZFE&usp=drivesdk',
   'createdTime': '2014-09-27T22:24:52.240Z',
   'modifiedTime': '2014-09-27T22:24:52.240Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJZTRjQ3doVVgyd00',
   'name': 'Audio',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20672',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJZTRjQ3doVVgyd00&usp=drivesdk',
   'createdTime': '2014-05-16T19:23:49.005Z',
   'modifiedTime': '2014-05-16T19:23:49.005Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJTk9kdVY5TkFPUFE',
   'name': 'Networking',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20734',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJTk9kdVY5TkFPUFE&usp=drivesdk',
   'createdTime': '2014-05-12T13:57:01.616Z',
   'modifiedTime': '2014-05-12T13:57:21.360Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJYmZmdnlkOVZya2c',
   'name': 'GGP',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20670',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJYmZmdnlkOVZya2c&usp=drivesdk',
   'createdTime': '2014-04-04T17:28:17.504Z',
   'modifiedTime': '2014-05-12T13:56:48.091Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJWFRLSHltcmdHRDA',
   'name': 'sayname',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20814',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJWFRLSHltcmdHRDA&usp=drivesdk',
   'createdTime': '2014-03-31T15:56:30.154Z',
   'modifiedTime': '2014-03-31T15:56:30.154Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0B8IkoNBph4qJb1F2S3RQRVl0UzQ',
   'name': 'mYgAmes',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
       '0AMIkoNBph4qJUk9PVA'
   ],
   'version': '20668',
   'webViewLink': 'https://docs.google.com/folderview?id=0B8IkoNBph4qJb1F2S3RQRVl0UzQ&usp=drivesdk',
   'createdTime': '2013-12-29T22:28:42.365Z',
   'modifiedTime': '2014-01-04T03:03:30.778Z',
   "capabilities": {
       "canEdit": True
   }
  },
  {

   'kind': 'drive#file',
   'id': '0Bx_h7N2n3_3VZE5RZXJGTDIyVnc',
   'name': 'Conqueror of Kingdoms',
   'mimeType': 'application/vnd.google-apps.folder',
   'trashed': False,
   'parents': [
   ],
   'version': '13537',
   'webViewLink': 'https://docs.google.com/folderview?id=0Bx_h7N2n3_3VZE5RZXJGTDIyVnc&usp=drivesdk',
   'createdTime': '2013-09-27T01:06:01.911Z',
   'modifiedTime': '2013-10-15T23:03:55.201Z',
   "capabilities": {
       "canEdit": True
   }
  }
 ]
}
