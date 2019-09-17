from rest_framework import status as http_status

from dataverse import Connection
from dataverse.exceptions import ConnectionError, UnauthorizedError, OperationFailedError

from framework.exceptions import HTTPError

from addons.dataverse import settings
from osf.utils.sanitize import strip_html

def _connect(host, token):
    try:
        return Connection(host, token)
    except ConnectionError:
        return None


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
    try:
        connection = _connect(host, token)
        if not connection:
            raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
        return connection
    except UnauthorizedError:
        raise HTTPError(http_status.HTTP_401_UNAUTHORIZED)


def connect_from_settings_or_401(node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    host = node_settings.external_account.oauth_key
    token = node_settings.external_account.oauth_secret

    return connect_or_error(host, token)


def get_files(dataset, published=False):
    version = 'latest-published' if published else 'latest'
    return dataset.get_files(version)


def publish_dataverse(dataverse):
    try:
        dataverse.publish()
    except OperationFailedError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)


def publish_dataset(dataset):
    if dataset.get_state() == 'RELEASED':
        raise HTTPError(http_status.HTTP_409_CONFLICT, data=dict(
            message_short='Dataset conflict',
            message_long='This version of the dataset has already been published.'
        ))
    if not dataset.dataverse.is_published:
        raise HTTPError(http_status.HTTP_405_METHOD_NOT_ALLOWED, data=dict(
            message_short='Method not allowed',
            message_long='A dataset cannot be published until its parent Dataverse is published.'
        ))

    try:
        dataset.publish()
    except OperationFailedError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)


def get_datasets(dataverse):
    if dataverse is None:
        return []
    return dataverse.get_datasets(timeout=settings.REQUEST_TIMEOUT)


def get_dataset(dataverse, doi):
    if dataverse is None:
        return
    dataset = dataverse.get_dataset_by_doi(doi, timeout=settings.REQUEST_TIMEOUT)
    try:
        if dataset and dataset.get_state() == 'DEACCESSIONED':
            raise HTTPError(http_status.HTTP_410_GONE, data=dict(
                message_short='Dataset deaccessioned',
                message_long='This dataset has been deaccessioned and can no longer be linked to the OSF.'
            ))
        return dataset
    except UnicodeDecodeError:
        raise HTTPError(http_status.HTTP_406_NOT_ACCEPTABLE, data=dict(
            message_short='Not acceptable',
            message_long='This dataset cannot be connected due to forbidden '
                         'characters in one or more of the file names.'
        ))


def get_dataverses(connection):
    if connection is None:
        return []
    return connection.get_dataverses()


def get_dataverse(connection, alias):
    if connection is None:
        return
    return connection.get_dataverse(alias)


def get_custom_publish_text(connection):
    if connection is None:
        return ''
    return strip_html(connection.get_custom_publish_text(), tags=['strong', 'li', 'ul'])
