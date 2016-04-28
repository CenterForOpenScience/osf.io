__all__ = ['DMPTool']

import httplib as http

from framework.exceptions import HTTPError
from website.addons.dmptool import settings

import requests
import urlparse


def connect_from_settings(node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    host = node_settings.external_account.oauth_key
    token = node_settings.external_account.oauth_secret

    try:
        return _connect(host, token)
    except UnauthorizedError:
        return None


def connect_or_error(host, token):

    # TO DO -- actually do a check if possible
    # https://github.com/CDLUC3/dmptool/issues/183

    # in the mean time return a DMPTool

    # need to change DMPTool to account for host
    return DMPTool(token, host)

    # try:
    #     connection = _connect(host, token)
    #     if not connection:
    #         raise HTTPError(http.SERVICE_UNAVAILABLE)
    #     return connection
    # except UnauthorizedError:
    #     raise HTTPError(http.UNAUTHORIZED)


def connect_from_settings_or_401(node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    host = node_settings.external_account.oauth_key
    token = node_settings.external_account.oauth_secret

    return connect_or_error(host, token)


def get_files(dataset, published=False):
    version = 'latest-published' if published else 'latest'
    return dataset.get_files(version)


def publish_dmptool(dmptool):
    try:
        dmptool.publish()
    except OperationFailedError:
        raise HTTPError(http.BAD_REQUEST)


def publish_dataset(dataset):
    if dataset.get_state() == 'RELEASED':
        raise HTTPError(http.CONFLICT, data=dict(
            message_short='Dataset conflict',
            message_long='This version of the dataset has already been published.'
        ))
    if not dataset.dmptool.is_published:
        raise HTTPError(http.METHOD_NOT_ALLOWED, data=dict(
            message_short='Method not allowed',
            message_long='A dataset cannot be published until its parent Dmptool is published.'
        ))

    try:
        dataset.publish()
    except OperationFailedError:
        raise HTTPError(http.BAD_REQUEST)


def get_datasets(dmptool):
    if dmptool is None:
        return []
    return dmptool.get_datasets(timeout=settings.REQUEST_TIMEOUT)


def get_dataset(dmptool, doi):
    if dmptool is None:
        return
    dataset = dmptool.get_dataset_by_doi(doi, timeout=settings.REQUEST_TIMEOUT)
    try:
        if dataset and dataset.get_state() == 'DEACCESSIONED':
            raise HTTPError(http.GONE, data=dict(
                message_short='Dataset deaccessioned',
                message_long='This dataset has been deaccessioned and can no longer be linked to the OSF.'
            ))
        return dataset
    except UnicodeDecodeError:
        raise HTTPError(http.NOT_ACCEPTABLE, data=dict(
            message_short='Not acceptable',
            message_long='This dataset cannot be connected due to forbidden '
                         'characters in one or more of the file names.'
        ))


def get_dmptools(connection):
    if connection is None:
        return []
    return connection.get_dmptools()


def get_dmptool(connection, alias):
    if connection is None:
        return
    return connection.get_dmptool(alias)


class DMPTool(object):
    def __init__(self, token, host="dmptool.org"):
        self.token = token
        self.host = host
        self.base_url = "https://{}/api/v1/".format(host)
        self.headers = {'Authorization': 'Token token={}'.format(self.token)}
                
    def get_url(self, path, headers=None):
        if headers is None:
            headers = self.headers
            
        url = self.base_url + path
        response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        return response 

    def plans(self, id_=None):
        """
        https://dmptool.org/api/v1/plans
        https://dmptool.org/api/v1/plans/:id
        """
        
        if id_ is None:
            return self.get_url("plans").json()
        else:
            return self.get_url("plans/{}".format(id_)).json()
                    
    def plans_full(self, id_=None, format_='json'):
    
        if id_ is None:
            # a json doc for to represent all public docs
            # I **think** if we include token, will get only docs owned
            return self.get_url("plans_full/", headers={}).json()
        else:
            if format_ == 'json':
                return self.get_url("plans_full/{}".format(id_)).json()
            elif format_ in ['pdf', 'docx']:
                return self.get_url("plans_full/{}.{}".format(id_, format_)).content
            else: 
                return None

    def plans_owned(self):
        return self.get_url("plans_owned").json()
    
    def plans_owned_full(self):
        return self.get_url("plans_owned_full").json()
    
    def plans_templates(self):
        return self.get_url("plans_templates").json()
        
    def institutions_plans_count(self):
        """
        https://github.com/CDLUC3/dmptool/wiki/API#for-a-list-of-institutions-and-plans-count
        """
        plans_counts = self.get_url("institutions_plans_count").json()
        return plans_counts

    
