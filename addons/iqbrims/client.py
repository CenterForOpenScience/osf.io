# -*- coding: utf-8 -*-
import json
import requests
import logging
import string

from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.iqbrims import settings

logger = logging.getLogger(__name__)


class IQBRIMSAuthClient(BaseClient):

    def userinfo(self, access_token):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'userinfo'),
            params={'access_token': access_token},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()


class IQBRIMSClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    def about(self):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'about', ),
            expects=(200, ),
            throws=HTTPError(401)
        ).json()

    def get_folder_link(self, folder_id='root'):
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
            folder_id),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['alternateLink']

    def folders(self, folder_id='root'):
        query = ' and '.join([
            "'{0}' in parents".format(folder_id),
            'trashed = false',
            "mimeType = 'application/vnd.google-apps.folder'",
        ])
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            params={'q': query},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['items']

    def files(self, folder_id='root'):
        query = ' and '.join([
            "'{0}' in parents".format(folder_id),
            'trashed = false',
        ])
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            params={'q': query},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['items']

    def create_folder(self, folder_id, title):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': title,
                'parents': [{
                    'id': folder_id
                }],
                'mimeType': 'application/vnd.google-apps.folder',
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def rename_folder(self, folder_id, title):
        res = self._make_request(
            'PUT',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
                            folder_id),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': title,
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def create_folder_if_not_exists(self, folder_id, title):
        items = self.folders(folder_id)
        exists = filter(lambda item: item['title'] == title, items)

        if len(exists) > 0:
            return False, exists[0]
        else:
            return True, self.create_folder(folder_id, title)

    def create_spreadsheet(self, folder_id, title):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': title,
                'parents': [{
                    'id': folder_id
                }],
                'mimeType': 'application/vnd.google-apps.spreadsheet',
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def create_spreadsheet_if_not_exists(self, folder_id, title):
        items = self.files(folder_id)
        exists = filter(lambda item: item['title'] == title, items)

        if len(exists) > 0:
            return False, exists[0]
        else:
            return True, self.create_spreadsheet(folder_id, title)


class SpreadsheetClient(BaseClient):

    def __init__(self, resource_id, access_token=None):
        self.resource_id = resource_id
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    def sheets(self):
        res = self._make_request(
            'GET',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['sheets']

    def add_sheet(self, title):
        res = self._make_request(
            'POST',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id + ':batchUpdate'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': title,
                            'index': 0
                        }
                    }
                }]
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def get_row_values(self, sheet_id, column_index, row_max):
        r = u'{0}!{1}2:{1}{2}'.format(sheet_id, self._row_name(column_index),
                                      row_max)
        res = self._make_request(
            'GET',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', r),
            expects=(200, ),
            throws=HTTPError(401)
        )
        data = res.json()
        return self._as_rows(data['values'], data['majorDimension']) \
               if 'values' in data else []

    def add_row(self, sheet_id, values):
        r = u'{0}!A1:{1}1'.format(sheet_id, self._row_name(len(values) + 1))
        res = self._make_request(
            'POST',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', r + ':append'),
            params={'valueInputOption': 'RAW'},
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'range': r,
                'values': [values],
                'majorDimension': 'ROWS'
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('Inserted: {}'.format(res.json()))

    def update_row(self, sheet_id, values, update_at):
        r = u'{0}!A{2}:{1}{2}'.format(sheet_id,
                                      self._row_name(len(values) + 1),
                                      update_at + 2)
        res = self._make_request(
            'PUT',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', r),
            params={'valueInputOption': 'RAW'},
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'range': r,
                'values': [values],
                'majorDimension': 'ROWS'
            }),
            expects=(200, 400, ),
            throws=HTTPError(401)
        )
        logger.info('Updated: {}'.format(res.json()))

    def get_row(self, sheet_id, get_at, length):
        r = u'{0}!A{2}:{1}{2}'.format(sheet_id,
                                      self._row_name(length),
                                      get_at + 2)
        res = self._make_request(
            'GET',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', r),
            expects=(200, ),
            throws=HTTPError(401)
        )
        data = res.json()
        return self._as_columns(data['values'], data['majorDimension']) \
               if 'values' in data else []

    def ensure_columns(self, sheet_id, columns):
        r = u'{}!A1:W1'.format(sheet_id)
        res = self._make_request(
            'GET',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', r),
            expects=(200, ),
            throws=HTTPError(401)
        )
        data = res.json()
        ecolumns = self._as_columns(data['values'], data['majorDimension']) \
                   if 'values' in data else []
        logger.info('Columns: {}'.format(ecolumns))
        new_columns = [c for c in columns if c not in ecolumns]
        if len(new_columns) == 0:
            return ecolumns
        new_r = u'{}!{}1:{}1'.format(sheet_id,
                                     self._row_name(len(ecolumns)),
                                     self._row_name(len(ecolumns) +
                                                    len(new_columns)))
        res = self._make_request(
            'PUT',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id, 'values', new_r),
            params={'valueInputOption': 'RAW'},
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'range': new_r,
                'values': [new_columns],
                'majorDimension': 'ROWS'
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('Updated: {}'.format(res.json()))
        return ecolumns + new_columns

    def _row_name(self, index):
        return string.ascii_uppercase[index]

    def _as_columns(self, values, major_dimension):
        if major_dimension == 'ROWS':
            return values[0]
        else:
            return [v[0] for v in values]

    def _as_rows(self, values, major_dimension):
        if major_dimension == 'COLUMNS':
            return values[0]
        else:
            return [v[0] for v in values]


class IQBRIMSFlowableClient(object):

    def __init__(self, app_id):
        self.app_id = app_id

    def start_workflow(self, project_id, project_title, status, secret):
        url = '{}service/runtime/process-instances'.format(settings.FLOWABLE_HOST)
        is_directly_submit_data = status['is_directly_submit_data'] \
                                  if 'is_directly_submit_data' in status \
                                  else False
        payload = {'processDefinitionId': self.app_id,
                   'variables': [{'name': 'projectId',
                                  'type': 'string',
                                  'value': '{}'.format(project_id)},
                                 {'name': 'paperTitle',
                                  'type': 'string',
                                  'value': project_title},
                                 {'name': 'isDirectlySubmitData',
                                  'type': 'boolean',
                                  'value': is_directly_submit_data},
                                 {'name': 'flowableWorkflowUrl',
                                  'type': 'string',
                                  'value': settings.FLOWABLE_TASK_URL},
                                 {'name': 'secret',
                                  'type': 'string',
                                  'value': secret}]}
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        response = requests.post(url, data=json.dumps(payload),
                                 headers=headers,
                                 auth=(settings.FLOWABLE_USER,
                                       settings.FLOWABLE_PASSWORD))
        logger.info('flowable-rest: response={}'.format(response.content))
        response.raise_for_status()
