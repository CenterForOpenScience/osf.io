# -*- coding: utf-8 -*-
# Drive credentials
CLIENT_ID = 'chaneme'
CLIENT_SECRET = 'changeme'

#https://developers.google.com/identity/protocols/OAuth2#expiration
EXPIRY_TIME = 60 * 60 * 24 * 175  # 175 days
REFRESH_TIME = 5 * 60  # 5 minutes


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
                            ('Authors', None),
                            ('Journal Name', 'journal_name'),
                            ('Publish Date', 'publish_date'),
                            ('Volume', 'volume'),
                            ('Page Number', 'page_number'),
                            ('Current Status', 'workflow_overall_state'),
                            ('Manuscript', None),
                            ('Raw data', None),
                            ('Checklist', None),
                            ('Folder', '_drive_url')]
APPSHEET_CHECK_COLUMNS = [('Updated', '_updated'),
                          (u'Project ID', '_node_id'),
                          ('Account', '_node_owner'),
                          ('Mail address', '_node_mail'),
                          ('Laboratory', '_labo_name'),
                          ('Title', '_node_title'),
                          ('Authors', None),
                          ('Comment', None),
                          ('Current Status', 'workflow_overall_state'),
                          ('Manuscript', None),
                          ('Folder', '_drive_url')]

FLOWABLE_HOST = 'http://localhost:9977/flowable-rest/'
FLOWABLE_RESEARCH_APP_ID = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
FLOWABLE_USER = 'testuser'
FLOWABLE_PASSWORD = 'testpass'
FLOWABLE_TASK_URL = 'http://localhost:9999/flowable-task/'

LABO_LIST = [{'id': 'rna', 'text': 'RNA分野'},
             {'id': 'xxx', 'text': 'XXX分野'},
             {'id': 'yyy', 'text': 'YYY分野'}]
