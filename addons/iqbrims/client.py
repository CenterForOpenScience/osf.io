# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import string

from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.iqbrims import settings

logger = logging.getLogger(__name__)
_user_settings_cache = {}

FILE_ENTRY_MARGIN = 3


def _ensure_string(access_token):
    if isinstance(access_token, bytes):
        return access_token.decode('utf8')
    return access_token


class IQBRIMSAuthClient(BaseClient):

    def userinfo(self, access_token):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'userinfo'),
            params={'access_token': _ensure_string(access_token)},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()


class IQBRIMSClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            access_token = _ensure_string(self.access_token)
            return {'authorization': 'Bearer {}'.format(access_token)}
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
        if len(permissions) > 0:
            for p in permissions:
                res = self._make_request(
                    'PATCH',
                    self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
                    file_id, 'permissions', p['id']),
                    headers={
                        'Content-Type': 'application/json',
                    },
                    data=json.dumps({
                        'role': 'writer',
                    }),
                    expects=(200, ),
                    throws=HTTPError(401)
                )
        else:
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

    def revoke_access_from_anyone(self, file_id, drop_all=True):
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
        if not drop_all:
            for p in permissions:
                res = self._make_request(
                    'PATCH',
                    self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
                    file_id, 'permissions', p['id']),
                    headers={
                        'Content-Type': 'application/json',
                    },
                    data=json.dumps({
                        'role': 'reader',
                    }),
                    expects=(200, ),
                    throws=HTTPError(401)
                )
        else:
            for p in permissions:
                res = self._make_request(
                    'DELETE',
                    self._build_url(settings.API_BASE_URL, 'drive', 'v3', 'files',
                    file_id, 'permissions', p['id']),
                    expects=(200, 204, 404, ),
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

    def create_content(self, folder_id, title, mime_type, content):
        params = {
            'title': title,
            'parents': [{
                'id': folder_id
            }]
        }
        metadata = ('metadata', json.dumps(params), 'application/json; charset=UTF-8')
        files = {'data': metadata, 'file': (title, content, mime_type)}
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'upload', 'drive', 'v2',
                            'files') + '?uploadType=multipart',
            files=files,
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def update_content(self, file_id, mime_type, content):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'upload', 'drive', 'v2',
                            'files', file_id) + '?uploadType=media',
            headers={
                'Content-Type': mime_type,
            },
            data=content,
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
        return res.content

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

    def delete_file(self, file_id):
        res = self._make_request(
            'DELETE',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
                            file_id),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def create_folder_if_not_exists(self, folder_id, title):
        items = self.folders(folder_id)
        exists = [item for item in items if item['title'] == title]

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
        exists = [item for item in items if item['title'] == title]

        if len(exists) > 0:
            return False, exists[0]
        else:
            return True, self.create_spreadsheet(folder_id, title)

    def copy_file(self, src_file_id, folder_id, title):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files',
                            src_file_id, 'copy'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': title,
                'parents': [{
                    'id': folder_id
                }],
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def copy_file_if_not_exists(self, src_file_id, folder_id, title):
        items = self.files(folder_id)
        exists = [item for item in items if item['title'] == title]

        if len(exists) > 0:
            return False, exists[0]
        else:
            return True, self.copy_file(src_file_id, folder_id, title)


class SpreadsheetClient(BaseClient):

    def __init__(self, resource_id, access_token=None):
        self.resource_id = resource_id
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            access_token = _ensure_string(self.access_token)
            return {'authorization': 'Bearer {}'.format(access_token)}
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

    def add_files(self, files_sheet_id, files_sheet_idx,
                  mgmt_sheet_id, mgmt_sheet_idx, files):
        top = {'depth': -1, 'name': None, 'files': [], 'dirs': []}
        max_depth = -1
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
        fc = self.ensure_columns(mgmt_sheet_id, ['Filled'], row=1)
        self.update_row(mgmt_sheet_id,
                        ['FALSE' if c == 'Filled' else '' for c in fc],
                        0)
        num_of_fcolumns = 2
        fcolumns = ['Remarks']
        entry_cols = ['L{}'.format(i) for i in range(0, max_depth + FILE_ENTRY_MARGIN)]
        COMMENT_MARGIN = 3
        c = self.ensure_columns(files_sheet_id,
                                entry_cols +
                                ['Extension (File)'] +
                                ['Persons Involved (File)'] +
                                ['{} (File)'.format(col) for col in fcolumns] +
                                ['Extension'] +
                                ['Software Used (Extension)'] +
                                ['{} (Extension)'.format(col) for col in fcolumns],
                                row=1 + COMMENT_MARGIN)
        values, styles = self._to_file_list(top, [])
        exts = sorted(set([self._get_ext(v) for v, t in values if t == 'file']))
        exts = [e for e in exts if len(e) > 0]
        exts += ['' for i in range(0, len(values) - len(exts))]
        values = [self._to_file_row(c, t, v, ex)
                  for (v, t), ex in zip(values, exts)]
        r = u'{0}!A{2}:{1}{2}'.format(files_sheet_id, self._row_name(len(c)), 1 + COMMENT_MARGIN)
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
        FILE_EXTRA_COLUMNS = 1  # Ext
        logger.info('Inserted: {}'.format(res.json()))
        ext_col_index = max_depth + FILE_EXTRA_COLUMNS + FILE_ENTRY_MARGIN + num_of_fcolumns
        col_count = ext_col_index + 1 + num_of_fcolumns

        hide_col_reqs = [{
            'updateDimensionProperties': {
                'range': {
                    'sheetId': files_sheet_idx,
                    'dimension': 'COLUMNS',
                    'startIndex': i,
                    'endIndex': i + 1,
                },
                'properties': {
                    'hiddenByUser': True,
                },
                'fields': 'hiddenByUser',
            }
        } for i, col in enumerate(c) if col.startswith('L') and col not in entry_cols]

        update_style_reqs = [{
            'repeatCell': {
                'range': {
                    'sheetId': files_sheet_idx,
                    'startRowIndex': row + 1 + COMMENT_MARGIN,
                    'endRowIndex': row + 1 + COMMENT_MARGIN + 1,
                    'startColumnIndex': col,
                    'endColumnIndex': col + 1,
                },
                'cell': {
                    'userEnteredFormat': style,
                },
                'fields': self._to_fields('userEnteredFormat', list(style.keys()))
            }
        } for row, col, style in styles]

        res = self._make_request(
            'POST',
            self._build_url(settings.SHEETS_API_BASE_URL, 'v4', 'spreadsheets',
                            self.resource_id + ':batchUpdate'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'requests': [{
                    'addProtectedRange': {
                        'protectedRange': {
                            'range': {'sheetId': files_sheet_idx,
                                      'startColumnIndex': 0,
                                      'endColumnIndex': col_count,
                                      'startRowIndex': 0,
                                      'endRowIndex': 1},
                            'warningOnly': True
                        }
                    }
                }, {
                    'addProtectedRange': {
                        'protectedRange': {
                            'range': {'sheetId': files_sheet_idx,
                                      'startColumnIndex': 0,
                                      'endColumnIndex': col_count,
                                      'startRowIndex': 0 + COMMENT_MARGIN,
                                      'endRowIndex': 1 + COMMENT_MARGIN},
                            'warningOnly': True
                        }
                    }
                }, {
                    'addProtectedRange': {
                        'protectedRange': {
                            'range': {'sheetId': files_sheet_idx,
                                      'startColumnIndex': 0,
                                      'endColumnIndex': c.index('Extension (File)') + 1,
                                      'startRowIndex': 1 + COMMENT_MARGIN,
                                      'endRowIndex': 1 + COMMENT_MARGIN + len(values)},
                            'warningOnly': True
                        }
                    }
                }, {
                    'addProtectedRange': {
                        'protectedRange': {
                            'range': {'sheetId': files_sheet_idx,
                                      'startColumnIndex': ext_col_index,
                                      'endColumnIndex': ext_col_index + 1,
                                      'startRowIndex': 1 + COMMENT_MARGIN,
                                      'endRowIndex': 1 + COMMENT_MARGIN + len(values)},
                            'warningOnly': True
                        }
                    }
                }, {
                    'autoResizeDimensions': {
                        'dimensions': {'sheetId': files_sheet_idx,
                                       'dimension': 'COLUMNS',
                                       'startIndex': 1,
                                       'endIndex': max_depth + FILE_ENTRY_MARGIN}
                    }
                }] + hide_col_reqs + update_style_reqs
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.info('DataValidation Updated: {}'.format(res.json()))

    def _get_ext(self, values):
        return os.path.splitext(values[-1])[-1].lower()

    def _to_fields(self, parent, keys):
        if len(keys) == 0:
            return parent
        if len(keys) == 1:
            return parent + '.' + keys[0]
        return '{}({})'.format(parent, ','.join(keys))

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
            elif c == 'Extension (File)':
                e = '-' if typestr != 'file' else self._get_ext(values)
            r.append(e)
        return r

    def _to_file_list(self, target, blank, offset=0):
        ret = []
        styles = []
        col = target['depth'] + 1
        for i, f in enumerate(sorted(target['files'])):
            is_last = i == len(target['files']) - 1
            r = ['' for i in range(0, col + 1)]
            for j in range(col):
                if j == col - 1:
                    if is_last and 0 == len(target['dirs']):
                        r[j] = '└−−'
                    else:
                        r[j] = '├−−'
                else:
                    if not blank[j]:
                        r[j] = '│'
            r[col] = f
            ret.append((r, 'file'))
        for i, d in enumerate(sorted(target['dirs'], key=lambda x: x['name'])):
            is_last = i == len(target['dirs']) - 1
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
            r[col] = d['name']
            _offset = offset + len(ret)
            ret.append((r, 'directory'))
            styles.append((_offset, col, {
                'textFormat': {
                    'italic': True,
                    'bold': True,
                },
            }))
            next_blank = list(blank) + ([is_last] if col > 0 else [])
            _r, _styles = self._to_file_list(d, next_blank, offset=_offset + 1)
            ret += _r
            styles += _styles
        return ret, styles


class IQBRIMSWorkflowUserSettings(object):

    def __init__(self, access_token, folder_id):
        self.access_token = access_token
        self.folder_id = folder_id
        self._cache = None

    def load(self):
        if self._cache is not None:
            return self._cache
        global _user_settings_cache
        exp = datetime.timedelta(seconds=settings.USER_SETTINGS_CACHE_EXPIRATION_SEC)
        if 'loadedTime' in _user_settings_cache and \
           datetime.datetime.now() - _user_settings_cache['loadedTime'] < exp:
            self._cache = _user_settings_cache.copy()
            return self._cache
        client = IQBRIMSClient(self.access_token)
        files = client.files(self.folder_id)
        files = [f for f in files if f['title'] == settings.USER_SETTINGS_SHEET_FILENAME]
        if len(files) == 0:
            sheet = client.create_spreadsheet(self.folder_id, settings.USER_SETTINGS_SHEET_FILENAME)
        elif 'modifiedDate' in _user_settings_cache and files[0]['modifiedDate'] == _user_settings_cache['modifiedDate']:
            self._cache = _user_settings_cache.copy()
            return self._cache
        else:
            sheet = files[0]
        sclient = SpreadsheetClient(sheet['id'], self.access_token)
        sheets = [s
                  for s in sclient.sheets()
                  if s['properties']['title'] == settings.USER_SETTINGS_SHEET_SHEET_NAME]
        logger.debug(u'Spreadsheet: id={}, sheet={}'.format(sheet['id'], sheets))
        if len(sheets) == 0:
            sclient.add_sheet(settings.USER_SETTINGS_SHEET_SHEET_NAME)
            sheets = [s
                      for s in sclient.sheets()
                      if s['properties']['title'] == settings.USER_SETTINGS_SHEET_SHEET_NAME]
        assert len(sheets) == 1
        sheet_id = sheets[0]['properties']['title']
        columns = sclient.ensure_columns(sheet_id, ['Key', 'Value'])
        row_max = sheets[0]['properties']['gridProperties']['rowCount']
        keys = sclient.get_row_values(sheet_id, columns.index('Key'), row_max)
        values = sclient.get_row_values(sheet_id, columns.index('Value'), row_max)
        _user_settings_cache['loadedTime'] = datetime.datetime.now()
        _user_settings_cache['modifiedDate'] = files[0]['modifiedDate'] \
                                               if len(files) > 0 else None
        _user_settings_cache['settings'] = dict(zip(keys, values))
        self._cache = _user_settings_cache.copy()
        return self._cache

    @property
    def LABO_LIST(self):
        current = self.load()
        if 'LABO_LIST' in current['settings']:
            try:
                labos = json.loads(current['settings']['LABO_LIST'])
                if type(labos) != list:
                    return [{'id': 'error', 'text': u'Not list{}'.format(labos)}]
                for labo in labos:
                    if 'id' not in labo:
                        return [{'id': 'error', 'text': u'No id: {}'.format(labo)}]
                    if 'text' not in labo:
                        return [{'id': 'error', 'text': u'No text: {}'.format(labo)}]
                return labos
            except ValueError as e:
                return [{'id': 'error', 'text': u'JSON Error: {}'.format(e)}]
        return settings.LABO_LIST

    @property
    def FLOWABLE_HOST(self):
        current = self.load()
        if 'FLOWABLE_HOST' in current['settings']:
            return current['settings']['FLOWABLE_HOST']
        return settings.FLOWABLE_HOST

    @property
    def FLOWABLE_TASK_URL(self):
        current = self.load()
        if 'FLOWABLE_TASK_URL' in current['settings']:
            return current['settings']['FLOWABLE_TASK_URL']
        return settings.FLOWABLE_TASK_URL

    @property
    def FLOWABLE_USER(self):
        current = self.load()
        if 'FLOWABLE_USER' in current['settings']:
            return current['settings']['FLOWABLE_USER']
        return settings.FLOWABLE_USER

    @property
    def FLOWABLE_PASSWORD(self):
        current = self.load()
        if 'FLOWABLE_PASSWORD' in current['settings']:
            return current['settings']['FLOWABLE_PASSWORD']
        return settings.FLOWABLE_PASSWORD

    @property
    def FLOWABLE_RESEARCH_APP_ID(self):
        current = self.load()
        if 'FLOWABLE_RESEARCH_APP_ID' in current['settings']:
            return current['settings']['FLOWABLE_RESEARCH_APP_ID']
        return settings.FLOWABLE_RESEARCH_APP_ID

    @property
    def FLOWABLE_SCAN_APP_ID(self):
        current = self.load()
        if 'FLOWABLE_SCAN_APP_ID' in current['settings']:
            return current['settings']['FLOWABLE_SCAN_APP_ID']
        return settings.FLOWABLE_SCAN_APP_ID

    @property
    def FLOWABLE_DATALIST_TEMPLATE_ID(self):
        current = self.load()
        if 'FLOWABLE_DATALIST_TEMPLATE_ID' in current['settings']:
            return current['settings']['FLOWABLE_DATALIST_TEMPLATE_ID']
        return settings.FLOWABLE_DATALIST_TEMPLATE_ID

    @property
    def MESSAGES(self):
        current = self.load()
        if 'MESSAGES' in current['settings']:
            r = json.loads(current['settings']['MESSAGES'])
            for key in sorted(current['settings'].keys()):
                if not key.startswith('MESSAGES.'):
                    continue
                r.update(json.loads(current['settings'][key]))
            return r
        return settings.MESSAGES

    @property
    def INDEXSHEET_FILES_SHEET_NAME(self):
        current = self.load()
        if 'INDEXSHEET_FILES_SHEET_NAME' in current['settings']:
            return current['settings']['INDEXSHEET_FILES_SHEET_NAME']
        return settings.INDEXSHEET_FILES_SHEET_NAME

    @property
    def INDEXSHEET_MANAGEMENT_SHEET_NAME(self):
        current = self.load()
        if 'INDEXSHEET_MANAGEMENT_SHEET_NAME' in current['settings']:
            return current['settings']['INDEXSHEET_MANAGEMENT_SHEET_NAME']
        return settings.INDEXSHEET_MANAGEMENT_SHEET_NAME


class IQBRIMSFlowableClient(BaseClient):

    def __init__(self, app_id, user_settings=None):
        self.app_id = app_id
        self.user_settings = user_settings if user_settings is not None else settings

    def start_workflow(self, project_id, project_title, status, secret):
        url = '{}service/runtime/process-instances'.format(self.user_settings.FLOWABLE_HOST)
        is_directly_submit_data = status['is_directly_submit_data'] \
                                  if 'is_directly_submit_data' in status \
                                  else False
        register_type = status['state']
        labo_name = status['labo_id']
        labos = [l for l in self.user_settings.LABO_LIST
                 if l['id'] == labo_name]
        labo_display_name = labos[0]['text'] if len(labos) > 0 \
                            else u'LaboID:{}'.format(labo_name)
        labo_display_name_en = (labos[0]['en'] if 'en' in labos[0] else labos[0]['text']) \
                               if len(labos) > 0 else u'LaboID:{}'.format(labo_name)
        accepted_date = status['accepted_date'].split('T')[0] \
                        if 'accepted_date' in status else ''
        accepted_datetime = status['accepted_date'] \
                            if 'accepted_date' in status else ''
        has_paper = status['has_paper'] if 'has_paper' in status else True
        has_raw = status['has_raw'] if 'has_raw' in status else True
        has_checklist = status['has_checklist'] if 'has_checklist' in status else True
        input_overview = status['input_overview'] if 'input_overview' in status else ''

        payload = {'processDefinitionId': self.app_id,
                   'variables': [{'name': 'projectId',
                                  'type': 'string',
                                  'value': '{}'.format(project_id)},
                                 {'name': 'paperTitle',
                                  'type': 'string',
                                  'value': project_title},
                                 {'name': 'paperFolderPattern',
                                  'type': 'string',
                                  'value': u'{}/{}/%-{}/'.format(register_type,
                                                                 labo_name,
                                                                 project_id)},
                                 {'name': 'laboName',
                                  'type': 'string',
                                  'value': labo_display_name},
                                 {'name': 'laboNameEN',
                                  'type': 'string',
                                  'value': labo_display_name_en},
                                 {'name': 'isDirectlySubmitData',
                                  'type': 'boolean',
                                  'value': is_directly_submit_data},
                                 {'name': 'acceptedDate',
                                  'type': 'string',
                                  'value': accepted_date},
                                 {'name': 'acceptedDateTime',
                                  'type': 'string',
                                  'value': accepted_datetime},
                                 {'name': 'hasPaper',
                                  'type': 'boolean',
                                  'value': has_paper},
                                 {'name': 'hasRaw',
                                  'type': 'boolean',
                                  'value': has_raw},
                                 {'name': 'hasChecklist',
                                  'type': 'boolean',
                                  'value': has_checklist},
                                 {'name': 'inputOverview',
                                  'type': 'string',
                                  'value': input_overview},
                                 {'name': 'flowableWorkflowUrl',
                                  'type': 'string',
                                  'value': self.user_settings.FLOWABLE_TASK_URL},
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
            expects=(200, 201),
            throws=HTTPError(500)
        )
        logger.info('flowable-rest: response={}'.format(response.json()))

    @property
    def _auth(self):
        return (self.user_settings.FLOWABLE_USER, self.user_settings.FLOWABLE_PASSWORD)
