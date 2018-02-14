# -*- coding: utf-8 -*-

from addons.onedrive.models import OneDriveProvider
from addons.onedrive.tests.factories import OneDriveAccountFactory
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase


class OneDriveAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'onedrive'
    ExternalAccountFactory = OneDriveAccountFactory
    Provider = OneDriveProvider

    def set_node_settings(self, settings):
        super(OneDriveAddonTestCase, self).set_node_settings(settings)
        settings.folder_id = '1234567890'
        settings.folder_path = 'Drive/Camera Uploads'
        settings.external_account = self.external_account


raw_root_folder_response = [
    {
      'createdBy': {
        'application': {
          'displayName': 'local-cosdev',
          'id': '44174239'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T02:25:24.687Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITEzMi42MzYyMzQxMzUyNDg3NzAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzIuMA',
      'id': 'F4D50E400DFE7D4E!132',
      'lastModifiedBy': {
        'application': {
          'displayName': 'local-cosdev',
          'id': '44174239'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-23T02:25:24.877Z',
      'name': 'Apps',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 0,
      'webUrl': 'https://1drv.ms/f/s!AE59_g1ADtX0gQQ',
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T02:25:24.687Z',
        'lastModifiedDateTime': '2017-02-23T02:25:24.687Z'
      },
      'folder': {
        'childCount': 1
      },
      'specialFolder': {
        'name': 'apps'
      }
    },
    {
      'createdBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2015-12-17T19:56:12.63Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITEwNi42MzYyMjA5NjY3MzQ3MDAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMDYuMA',
      'id': 'F4D50E400DFE7D4E!106',
      'lastModifiedBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-07T20:37:53.47Z',
      'name': 'Documents',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 1056811,
      'webUrl': 'https://1drv.ms/f/s!AE59_g1ADtX0ag',
      'fileSystemInfo': {
        'createdDateTime': '2015-12-17T19:56:12.63Z',
        'lastModifiedDateTime': '2015-12-17T19:56:12.63Z'
      },
      'folder': {
        'childCount': 1
      },
      'specialFolder': {
        'name': 'documents'
      }
    },
    {
      'createdBy': {
        'application': {
          'displayName': 'local-cosdev',
          'id': '44174239'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T02:25:42.93Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITEzNC42MzYyMzQxMzU0MjkzMDAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzQuMA',
      'id': 'F4D50E400DFE7D4E!134',
      'lastModifiedBy': {
        'application': {
          'displayName': 'local-cosdev',
          'id': '44174239'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-23T02:25:42.93Z',
      'name': 'Music',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 0,
      'webUrl': 'https://1drv.ms/f/s!AE59_g1ADtX0gQY',
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T02:25:42.93Z',
        'lastModifiedDateTime': '2017-02-23T02:25:42.93Z'
      },
      'folder': {
        'childCount': 0
      },
      'specialFolder': {
        'name': 'music'
      }
    },
    {
      'createdBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2015-12-17T19:56:12.24Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITEwNS42MzYyMjA5Njk5MTgzMDAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMDUuMA',
      'id': 'F4D50E400DFE7D4E!105',
      'lastModifiedBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-07T20:43:11.83Z',
      'name': 'Pictures',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 13,
      'webUrl': 'https://1drv.ms/f/s!AE59_g1ADtX0aQ',
      'fileSystemInfo': {
        'createdDateTime': '2015-12-17T19:56:12.24Z',
        'lastModifiedDateTime': '2015-12-17T19:56:12.24Z'
      },
      'folder': {
        'childCount': 1
      },
      'specialFolder': {
        'name': 'photos'
      }
    },
    {
      'createdBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2015-12-17T19:56:30.89Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITEwNy42MzYwOTMxMzUyMDc4MDAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMDcuMA',
      'id': 'F4D50E400DFE7D4E!107',
      'lastModifiedBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2016-09-12T21:45:20.78Z',
      'name': 'Tenkum',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 1588779,
      'webUrl': 'https://1drv.ms/f/s!AE59_g1ADtX0aw',
      'fileSystemInfo': {
        'createdDateTime': '2015-12-17T19:56:30.89Z',
        'lastModifiedDateTime': '2015-12-17T19:56:30.89Z'
      },
      'folder': {
        'childCount': 5
      }
    },
    {
      'createdBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T07:27:44.253Z',
      'cTag': 'adDpGNEQ1MEU0MDBERkU3RDRFITE1NC42MzYyMzQzMTcxMDY2MzAwMDA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNTQuMA',
      'id': 'F4D50E400DFE7D4E!154',
      'lastModifiedBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-23T07:28:30.663Z',
      'name': 'foo',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 28359,
      'webUrl': 'https://1drv.ms/o/s!AE59_g1ADtX0gRo',
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T07:27:44.253Z',
        'lastModifiedDateTime': '2017-02-23T07:27:44.253Z'
      },
      'package': {
        'type': 'oneNote'
      }
    },
    {
      '@content.downloadUrl': 'https://public.bn1303.livefilestore.com/y3meR_7rVWrrLE-4_8eWU09UhEHrtVojgGVrPDBh3M8Qq0Iut6Y5-x68vBGXmra-p9X6d5PcWocISnjJQMa_nQ1QMw5HUTrT0AhFq6_hurW6lwJ0qBwlzsUYWzUoLfMu9KqdUnaBghT1NiMHSyPSlUO0UgAant5d85tXtn3xqy94i9yLzq8_6spoZ_ffgYX7l-FwQBRxaDz8q6LN7SFT1JQV9S_1Fr_BDCbtitKip_UgO0',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:11:31.37Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITEzNi4yNTg',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzYuMg',
      'id': 'F4D50E400DFE7D4E!136',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-23T03:11:41.32Z',
      'name': 'foo 1.txt',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 14,
      'webUrl': 'https://1drv.ms/t/s!AE59_g1ADtX0gQg',
      'file': {
        'hashes': {
          'crc32Hash': '82872CD6',
          'sha1Hash': '12779E2CF3B4108A897FC5C6A986D4F2A4BB9026'
        },
        'mimeType': 'text/plain'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:11:31.37Z',
        'lastModifiedDateTime': '2017-02-23T03:11:41.307Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3mLQF-L6CLmfw-0FIxfJo6dYEkn0E_rtkcPWNXiQ6SWdt68K9EzqVb08tgPAo3S-1gTFv0xhfRndRPGcz3Ed7fm6sTP4-A9tJ5NpMjMaVVRO9Ds60TdvDrv-C6N4xgG96dB73_pAXgu7pBwDszrCixFvU75WDNW4o2C8G2cSj9hs8',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:12:07.257Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITEzNy4yNjk',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzcuMTI',
      'id': 'F4D50E400DFE7D4E!137',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:21:56.633Z',
      'name': 'foo.docx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 15122,
      'webUrl': 'https://1drv.ms/w/s!AE59_g1ADtX0gQk',
      'file': {
        'hashes': {
          'crc32Hash': 'D8FEF070',
          'sha1Hash': 'DF4BA34A942459421A122AF0E9F8F2E3369174B7'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:12:07.257Z',
        'lastModifiedDateTime': '2017-02-23T03:12:52.63Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3mi1bPzwA871FD5vV5ylbGhndSxFcuzaP2W7SUmv6ythXicF6LoairKEJC1geR6jImpd4Zjeyrae__LKt0jdcM7wwOiWMqjbZ4g2ooLjmIyp0l8z3O-ic42SE2_UfLnW2jjMYeBQ3dFA-Jm_1qrml9Z759E0gRMKWMSsC3MjnfwSo',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T06:19:04.02Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE0OS4yNjk',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNDkuMTM',
      'id': 'F4D50E400DFE7D4E!149',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:22:00.88Z',
      'name': 'foo.pptx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 30523,
      'webUrl': 'https://1drv.ms/p/s!AE59_g1ADtX0gRU',
      'file': {
        'hashes': {
          'crc32Hash': '2CB42AEC',
          'sha1Hash': 'B75AE7590C5953B0157CBAB9DCBD1C2672F033FE'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T06:19:04.02Z',
        'lastModifiedDateTime': '2017-02-23T06:34:14.997Z'
      }
    },
    {
      '@content.downloadUrl': 'https://public.bn1303.livefilestore.com/y3mo0SZyPfHP8KaGX-1Sd2EyxdzpetQ56CC-Wnk4wAPEVUaAcbYMvqJG3JsdA5J65xQQMbL7u7GBKf-Av2aXngTjYyKV4efKHdKRCcMx0BdpuAZrexpCJmzU7AcdU5iHnsk5ItApBUlotO8hl1lZGFNRJfDclTOJujr45aEAeHI6CT16tAmxIH6DfiAC2l4iK_vJsilRFc-m32XBQU8HpiwXjigJiLxffP-KyEGsMIgooo',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:10:44.713Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITEzNS4yNTg',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzUuMg',
      'id': 'F4D50E400DFE7D4E!135',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-23T03:10:56.25Z',
      'name': 'foo.txt',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 14,
      'webUrl': 'https://1drv.ms/t/s!AE59_g1ADtX0gQc',
      'file': {
        'hashes': {
          'crc32Hash': '9E0BA90F',
          'sha1Hash': 'F8B9668ECA3938C835AF1E9DCACFA52603511FF3'
        },
        'mimeType': 'text/plain'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:10:44.713Z',
        'lastModifiedDateTime': '2017-02-23T03:10:56.237Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3mDcrFEI4yJFJe_Nb3oq2lZ_DXKDXaXWq4ZnUvsNQPCX4NlEQ3B1ypO4uUJ7XIzkh1q5bBUbUeRjEoNJberX70FAtY0L55GpYAPD4rlwwU83c6zTBmRB6b00Yd-I6xhXQSJ7hEVeklwoSURh0FZ-nMr3obVqsUnIzks46OQEPs7aQ',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:13:37.727Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE0NC4yNjU',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNDQuMTU',
      'id': 'F4D50E400DFE7D4E!144',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:21:58.38Z',
      'name': 'foo.xlsx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 8036,
      'webUrl': 'https://1drv.ms/x/s!AE59_g1ADtX0gRA',
      'file': {
        'hashes': {
          'crc32Hash': '2DCEE45F',
          'sha1Hash': '98927311DD9AE3966C9A7D4DAF4579A87C870EFB'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:13:37.727Z',
        'lastModifiedDateTime': '2017-02-23T03:24:53.483Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3mUbHeGrn5Qh1ZwPHCKp4czfgGAGz_-ePntZpq_47wbGU6VccDDTq2149EnUS9hoQ40V07lPVuSMv-2qBCwFqe40t5f0EBcrCJbFzNktZ0f_UrLNnMPBl1TemukaqqOXGY0iyqHvz-ole1jC_DsWo_t-2qGd2Oa8V_Veh8KK8UHsc',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:13:05.643Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE0Mi4yNzA',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNDIuMTI',
      'id': 'F4D50E400DFE7D4E!142',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:21:57.36Z',
      'name': 'foo1.docx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 14912,
      'webUrl': 'https://1drv.ms/w/s!AE59_g1ADtX0gQ4',
      'file': {
        'hashes': {
          'crc32Hash': '551418A8',
          'sha1Hash': 'FDA866479C801C92860ADA0AFD4C850F21078EE7'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:13:05.643Z',
        'lastModifiedDateTime': '2017-02-23T03:13:29.087Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3m8qKRRwHNq1a3YJo5b3HDCisfHEoIQfX-BrS62q2sNhZja3dPlT6qW0_CHhTA61M5_XnxdKknGE3Rg9Vv8NZN5-Xi72TQJGS16VhfgO53iyJxRml99FSXXrhkH-0y7iXrI4ibBuch7u7-m1sErEbgERviZ3RmD84HttNZg-Hn4kM',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T06:34:18.873Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE1Mi4yNzE',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNTIuMTc',
      'id': 'F4D50E400DFE7D4E!152',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:22:01.797Z',
      'name': 'foo1.pptx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 30701,
      'webUrl': 'https://1drv.ms/p/s!AE59_g1ADtX0gRg',
      'file': {
        'hashes': {
          'crc32Hash': 'ADD1D585',
          'sha1Hash': '0346CB868CD2C03B09341D4232AD2D38B459A699'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T06:34:18.873Z',
        'lastModifiedDateTime': '2017-02-23T07:27:07.12Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3mx4zP2_eOo43jA6xRHtVi7jfozdtka4XygTf4YsMrZJytqg9I36Fd43K6EpCxEH15163NKVkvQjiROuOn9m3xPtZzu-g3Pzt5hE8CHDsoS1iH36PgBkOd3P49-5GIW_Y_OJybBA3YkG64DHCPjSFftBrfdX5w-zxBTKXYBA3CGG0',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T03:45:08.03Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE0Ny4yNjU',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNDcuMjQ',
      'id': 'F4D50E400DFE7D4E!147',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:22:00.06Z',
      'name': 'foo1.xlsx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 8043,
      'webUrl': 'https://1drv.ms/x/s!AE59_g1ADtX0gRM',
      'file': {
        'hashes': {
          'crc32Hash': '7441963D',
          'sha1Hash': '0078FE7CF1088EECADEBD374905D0560FDF3FD97'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T03:45:08.03Z',
        'lastModifiedDateTime': '2017-02-23T06:18:59.52Z'
      }
    },
    {
      '@content.downloadUrl': 'https://kdqyaa.bn1303.livefilestore.com/y3m38TiJnMWVpml53HkELL0YRerqKsy8nK1lU3lZUYo48-EXez--3_TZ7VtE_L1sSnxx4VZ0q2fva_ICwHBkjzl8S2xgRzSNqLYfuklja6-770qju2Wrw8gQGeT58XBI6aaFuxa-pgPiYFiF6yAE4Ngj7LVeEx4dVW5BO51Gn4cY5o',
      'createdBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2017-02-23T07:29:04.897Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITE1OS4yNjY',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExNTkuMTc',
      'id': 'F4D50E400DFE7D4E!159',
      'lastModifiedBy': {
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2017-02-25T14:22:02.903Z',
      'name': 'foo2.xlsx',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 10541,
      'webUrl': 'https://1drv.ms/x/s!AE59_g1ADtX0gR8',
      'file': {
        'hashes': {
          'crc32Hash': 'B4AD5B8D',
          'sha1Hash': 'AAF14BB6C3E373A7C044A208A9D3A30DD100E293'
        },
        'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      },
      'fileSystemInfo': {
        'createdDateTime': '2017-02-23T07:29:04.897Z',
        'lastModifiedDateTime': '2017-02-23T07:30:04.57Z'
      }
    },
    {
      '@content.downloadUrl': 'https://public.bn1303.livefilestore.com/y3mZjrqNTRpDIy54W750IhRdbVbfh7RdFdtJ6Vmx6EIUuUVyGZTyy9CWwUFrWlnbmGtQ7OVKRnU9kkx_zN1hv-7HGSxBRRl3hjEcWgRcRoss4qCnNvmabwxW0J1rSc3oss1a8jj7J-hUmUDTa5EasvlsJPs9t8XmyuoF1PVgnTjOCyDjPpXDAjaziaojxWlQh0-t35XiXymBi4lfebfgf1a37RT1raPJ79pj1_KLJ5tgtE',
      'createdBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'createdDateTime': '2015-12-17T19:56:11.88Z',
      'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITEwNC4yNTc',
      'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMDQuMw',
      'id': 'F4D50E400DFE7D4E!104',
      'lastModifiedBy': {
        'application': {
          'displayName': 'OneDrive website',
          'id': '44048800'
        },
        'user': {
          'displayName': 'Fitz Elliott',
          'id': 'f4d50e400dfe7d4e'
        }
      },
      'lastModifiedDateTime': '2015-12-17T19:56:29.963Z',
      'name': 'Getting started with OneDrive.pdf',
      'parentReference': {
        'driveId': 'f4d50e400dfe7d4e',
        'id': 'F4D50E400DFE7D4E!103',
        'path': '/drive/root:'
      },
      'size': 1311269,
      'webUrl': 'https://1drv.ms/b/s!AE59_g1ADtX0aA',
      'file': {
        'hashes': {
          'crc32Hash': 'F8DDF9BE',
          'sha1Hash': 'A9C4ACF2DA75FC49056976433AC32142D2C71AB1'
        },
        'mimeType': 'application/pdf'
      },
      'fileSystemInfo': {
        'createdDateTime': '2015-12-17T19:56:11.88Z',
        'lastModifiedDateTime': '2015-12-17T19:56:11.88Z'
      }
    }
]

raw_subfolder_response = [
    {
        '@content.downloadUrl': 'https://public.bn1303.livefilestore.com/173450918374509173450',
        'createdBy': {
            'application': {
                'displayName': 'local-thingapp',
                'id': '994562945'
            },
            'user': {
                'displayName': 'Fitz Elliott',
                'id': '992349'
            }
        },
        'createdDateTime': '2017-02-07T20:37:50.73Z',
        'cTag': 'aYzpGNEQ1MEU0MDBERkU3RDRFITEzMC4yNTc',
        'eTag': 'aRjRENTBFNDAwREZFN0Q0RSExMzAuMw',
        'id': 'FE830D1CB134A0!130',
        'lastModifiedBy': {
            'application': {
                'displayName': 'local-THINGAPP',
                'id': '994562945'
            },
            'user': {
                'displayName': 'Fitz Elliott',
                'id': '992349'
            }
        },
        'lastModifiedDateTime': '2017-02-07T20:37:53.47Z',
        'name': 'Periodic Table of the Operators A4 300dpi.jpg',
        'parentReference': {
            'driveId': 'fe830d1cb134a0',
            'id': 'FE830D1CB134A0!130',
            'name': 'Documents',
            'path': '/drive/root:/Documents'
        },
        'size': 1056811,
        'webUrl': 'https://1drv.ms/i/s!LE93_m9sd3WJ82',
        'file': {
            'hashes': {
                'crc32Hash': 'B0D38EF0',
                'sha1Hash': 'DE751E0D3D8292A349A4698C59BDE514CD633589'
            },
            'mimeType': 'image/jpeg'
        },
        'fileSystemInfo': {
            'createdDateTime': '2017-02-07T20:37:50.73Z',
            'lastModifiedDateTime': '2017-02-07T20:37:50.73Z'
        },
        'image': {
            'height': 2456,
            'width': 3477
        },
        'photo': {
            'takenDateTime': '2017-02-07T20:37:50.73Z'
        }
    }
]


