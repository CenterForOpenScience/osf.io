# -*- coding: utf-8 -*-
import json
import requests
import logging

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
