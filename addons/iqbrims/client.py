# -*- coding: utf-8 -*-
import json
import logging
import os
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

    def get_file_link(self, file_id):
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
            file_id),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['alternateLink']

    def grant_access_from_anyone(self, file_id):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
            file_id, 'permissions'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'role': 'writer',
                'type': 'anyone',
                'allowFileDiscovery': False,
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def revoke_access_from_anyone(self, file_id):
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
            file_id, 'permissions'),
            expects=(200, ),
            throws=HTTPError(401)
        )
        permissions = res.json()['permissions']
        permissions = [p
                       for p in permissions
                       if 'type' in p and p['type'] == 'anyone']
        for p in permissions:
            res = self._make_request(
                'DELETE',
                self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
                file_id, 'permissions', p['id']),
                expects=(200, ),
                throws=HTTPError(401)
            )
        return permissions

    def get_folder_info(self, folder_id):
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
            folder_id),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def get_content(self, file_id):
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
            file_id),
            params={'alt': 'media'},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.text

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

    def get_column_values(self, sheet_id, row_index, col_max):
        r = u'{0}!A{1}:{2}{1}'.format(sheet_id, row_index,
                                      self._row_name(col_max))
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

    def ensure_columns(self, sheet_id, columns, row=1):
        r = u'{0}!A{1}:W{1}'.format(sheet_id, row)
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
        new_r = u'{0}!{1}{3}:{2}{3}'.format(sheet_id,
                                            self._row_name(len(ecolumns)),
                                            self._row_name(len(ecolumns) + len(new_columns)),
                                            row)
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

    def add_files(self, sheet_id, sheet_idx, files):
        top = {'depth': 0, 'name': None, 'files': [], 'dirs': []}
        max_depth = 0
        for f in files:
            if f.endswith('/'):
                continue
            if len(f.strip()) == 0:
                continue
            paths = f.split('/')
            target = top
            for i, p in enumerate(paths):
                if i == len(paths) - 1:
                    target['files'].append(p)
                    continue
                next_target = None
                for d in target['dirs']:
                    if p == d['name']:
                        next_target = d
                        break
                if next_target is None:
                    new_depth = target['depth'] + 1
                    d = {'depth': new_depth, 'name': p, 'files': [], 'dirs': []}
                    if max_depth < new_depth:
                        max_depth = new_depth
                    target['dirs'].append(d)
                    next_target = d
                target = next_target
        self.ensure_columns(sheet_id, ['Filled'], row=1)
        fcolumns = ['Persons Involved', 'Remarks', 'Software Used']
        c = self.ensure_columns(sheet_id,
                                ['L{}'.format(i)
                                 for i in range(0, max_depth + 2)] +
                                ['{}(File)'.format(col) for col in fcolumns] +
                                ['Extension'] +
                                ['{}(Extension)'.format(col) for col in fcolumns],
                                row=3)
        values = self._to_file_list(top, [])
        exts = sorted(set([os.path.splitext(v[-1])[-1]
                           for v, t in values if t == 'file']))
        exts = [e for e in exts if len(e) > 0]
        exts += ['' for i in range(0, len(values) - len(exts))]
        values = [self._to_file_row(c, t, v, ex)
                  for (v, t), ex in zip(values, exts)]
        r = u'{0}!A3:{1}3'.format(sheet_id, self._row_name(len(c)))
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
                'values': values,
                'majorDimension': 'ROWS'
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('Inserted: {}'.format(res.json()))
        res = self._make_request(
            'POST',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id + ':batchUpdate'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'requests': [{
                    'setDataValidation': {
                        'range': {'sheetId': sheet_idx,
                                  'startColumnIndex': 0,
                                  'endColumnIndex': 1,
                                  'startRowIndex': 1,
                                  'endRowIndex': 2},
                        'rule': {
                            'condition': {
                                'type': 'BOOLEAN'
                            }
                        }
                    }
                }]
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('DataValidation Updated: {}'.format(res.json()))

    def _row_name(self, index):
        if index < len(string.ascii_uppercase):
            return string.ascii_uppercase[index]
        base = index // len(string.ascii_uppercase)
        return string.ascii_uppercase[base - 1] + \
               string.ascii_uppercase[index % len(string.ascii_uppercase)]

    def _as_columns(self, values, major_dimension):
        if major_dimension == 'ROWS':
            return values[0]
        else:
            return [v[0] if len(v) > 0 else '' for v in values]

    def _as_rows(self, values, major_dimension):
        if major_dimension == 'COLUMNS':
            return values[0]
        else:
            return [v[0] if len(v) > 0 else '' for v in values]

    def _to_file_row(self, columns, typestr, values, ext):
        r = []
        for c in columns:
            e = ''
            if c.startswith('L'):
                index = int(c[1:])
                e = values[index] if index < len(values) else ''
            elif c == 'Extension':
                e = ext
            r.append(e)
        return r

    def _to_file_list(self, target, blank):
        ret = []
        col = target['depth'] + 1
        for i, d in enumerate(sorted(target['dirs'], key=lambda x: x['name'])):
            is_last = i == len(target['dirs']) - 1
            r = ['' for i in range(0, col + 1)]
            for j in range(col):
                if j == col - 1:
                    if is_last and 0 == len(target['files']):
                        r[j] = '└−−'
                    else:
                        r[j] = '├−−'
                else:
                    if not blank[j]:
                        r[j] = '│'
            r[col] = d['name']
            ret.append((r, 'directory'))
            next_blank = list(blank)
            next_blank.append(is_last and 0 == len(target['files']))
            ret += self._to_file_list(d, next_blank)
        for i, f in enumerate(sorted(target['files'])):
            is_last = i == len(target['files']) - 1
            r = ['' for i in range(0, col + 1)]
            for j in range(col):
                if j == col - 1:
                    if is_last:
                        r[j] = '└−−'
                    else:
                        r[j] = '├−−'
                else:
                    if not blank[j]:
                        r[j] = '│'
            r[col] = f
            ret.append((r, 'file'))
        return ret


class IQBRIMSFlowableClient(BaseClient):

    def __init__(self, app_id):
        self.app_id = app_id

    def start_workflow(self, project_id, project_title, status, secret):
        url = '{}service/runtime/process-instances'.format(settings.FLOWABLE_HOST)
        is_directly_submit_data = status['is_directly_submit_data'] \
                                  if 'is_directly_submit_data' in status \
                                  else False
        register_type = status['state']
        labo_name = status['labo_id']
        labos = [l['text'] for l in settings.LABO_LIST
                 if l['id'] == labo_name]
        labo_display_name = labos[0] if len(labos) > 0 \
                            else 'LaboID:{}'.format(labo_name)
        accepted_date = status['accepted_date'].split('T')[0] \
                        if 'accepted_date' in status else ''
        payload = {'processDefinitionId': self.app_id,
                   'variables': [{'name': 'projectId',
                                  'type': 'string',
                                  'value': '{}'.format(project_id)},
                                 {'name': 'paperTitle',
                                  'type': 'string',
                                  'value': project_title},
                                 {'name': 'paperFolderPattern',
                                  'type': 'string',
                                  'value': '{}/{}/%-{}/'.format(register_type,
                                                                labo_name,
                                                                project_id)},
                                 {'name': 'laboName',
                                  'type': 'string',
                                  'value': labo_display_name},
                                 {'name': 'isDirectlySubmitData',
                                  'type': 'boolean',
                                  'value': is_directly_submit_data},
                                 {'name': 'acceptedDate',
                                  'type': 'string',
                                  'value': accepted_date},
                                 {'name': 'flowableWorkflowUrl',
                                  'type': 'string',
                                  'value': settings.FLOWABLE_TASK_URL},
                                 {'name': 'secret',
                                  'type': 'string',
                                  'value': secret}]}
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        response = self._make_request(
            'POST',
            url,
            headers=headers,
            data=json.dumps(payload),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('flowable-rest: response={}'.format(response.json()))

    @property
    def _auth(self):
        return (settings.FLOWABLE_USER, settings.FLOWABLE_PASSWORD)
