# -*- coding: utf-8 -*-

import json
import os

from website.settings import parent_dir

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(parent_dir(HERE), 'static')

# Drive credentials
CLIENT_ID = 'chaneme'
CLIENT_SECRET = 'changeme'

#https://developers.google.com/identity/protocols/OAuth2#expiration
EXPIRY_TIME = 60 * 60 * 24 * 175  # 175 days
REFRESH_TIME = 5 * 60  # 5 minutes

with open(os.path.join(STATIC_PATH, 'iqbrimsLogActionList.json')) as fp:
    LOG_MESSAGES = json.load(fp)

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive',
]
OAUTH_BASE_URL = 'https://accounts.google.com/o/oauth2/'
API_BASE_URL = 'https://www.googleapis.com/'
SHEETS_API_BASE_URL = 'https://sheets.googleapis.com/'

APPSHEET_FILENAME = 'IQB-RIMS'
APPSHEET_SHEET_NAME = 'Registrations'
APPSHEET_DEPOSIT_COLUMNS = [('Updated', '_updated'),
                            (u'Project ID', '_node_id'),
                            ('Account', '_node_owner'),
                            ('Mail address', '_node_mail'),
                            ('Laboratory', '_labo_name'),
                            ('Title', '_node_title'),
                            ('Authors', '_node_contributors'),
                            ('Comment', 'files_comment'),
                            ('Journal Name', 'journal_name'),
                            ('Publish Date', 'publish_date'),
                            ('Volume', 'volume'),
                            ('Page Number', 'page_number'),
                            ('Current Status', 'workflow_overall_state'),
                            ('Manuscript', 'workflow_paper_updated'),
                            ('Raw data', 'workflow_raw_updated'),
                            ('Checklist', 'workflow_checklist_updated'),
                            ('Folder', '_drive_url')]
APPSHEET_CHECK_COLUMNS = [('Updated', '_updated'),
                          (u'Project ID', '_node_id'),
                          ('Account', '_node_owner'),
                          ('Mail address', '_node_mail'),
                          ('Laboratory', '_labo_name'),
                          ('Title', '_node_title'),
                          ('Authors', '_node_contributors'),
                          ('Comment', 'files_comment'),
                          ('Current Status', 'workflow_overall_state'),
                          ('Manuscript', 'workflow_paper_updated'),
                          ('Folder', '_drive_url')]
INDEXSHEET_FILENAME = 'Raw Files'
INDEXSHEET_FILES_SHEET_NAME = 'Files'
INDEXSHEET_MANAGEMENT_SHEET_NAME = 'Management'

IMAGELIST_FOLDERNAME = u'スキャン画像'
IMAGELIST_FILENAME = 'files.txt'

FLOWABLE_HOST = 'http://localhost:9977/flowable-rest/'
FLOWABLE_RESEARCH_APP_ID = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
FLOWABLE_SCAN_APP_ID = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
FLOWABLE_USER = 'testuser'
FLOWABLE_PASSWORD = 'testpass'
FLOWABLE_TASK_URL = 'http://localhost:9999/flowable-task/'

FLOWABLE_DATALIST_TEMPLATE_ID = None

LABO_LIST = [{'id': 'rna', 'text': u'RNA分野', 'en': 'Laboratory of RNA'},
             {'id': 'xxx', 'text': u'XXX分野', 'en': 'Laboratory of XXX'},
             {'id': 'yyy', 'text': u'YYY分野', 'en': 'Laboratory of YYY'}]

MESSAGES = {}

USER_SETTINGS_SHEET_FILENAME = 'Settings'
USER_SETTINGS_SHEET_SHEET_NAME = 'Settings'
USER_SETTINGS_CACHE_EXPIRATION_SEC = 60
