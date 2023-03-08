import logging
import requests
from requests.exceptions import HTTPError


logger = logging.getLogger(__name__)


def _flatten_indices(indices):
    r = []
    for i in indices:
        r.append(i)
        r += _flatten_indices(i.children)
    return r


class Client(object):
    """
    WEKO Client
    """
    host = None
    token = None
    username = None
    password = None

    def __init__(self, host, token=None, username=None, password=None):
        self.host = host
        self.token = token
        self.username = username
        self.password = password
        if not self.host.endswith('/'):
            self.host += '/'

    def get_login_user(self, default_user=None):
        resp = requests.get(self._base_host + 'api/get_profile_info/', **self._requests_args())
        if resp.status_code != 200:
            resp.raise_for_status()
        if self.username is not None:
            default_user = self.username
        logger.debug(f'WEKO service-document headers={resp.headers}, json={resp.json()}')
        results = resp.json().get('results', {})
        return results.get('subitem_mail_address', default_user)

    def get_indices(self):
        """
        Get all indices from the WEKO.
        """
        root = self._get('api/tree')
        indices = []
        for desc in root:
            indices.append(Index(self, desc))
        return indices

    def get_index_by_id(self, index_id):
        indices = [i for i in _flatten_indices(self.get_indices()) if str(i.identifier) == str(index_id)]
        if len(indices) == 0:
            raise ValueError(f'No index for id = {index_id}')
        return indices[0]

    def get_item_records_url(self, item_id):
        return self._base_host + 'records/' + item_id

    def get_index_items_url(self, index_id):
        return self._base_host + 'search?search_type=2&q=' + index_id

    def deposit(self, files, headers=None):
        return self._post('sword/service-document', files=files, headers=headers)

    def request_headers(self, headers=None):
        return self._requests_args(headers=headers).get('headers', {})

    @property
    def _base_host(self):
        if not self.host.endswith('/sword/'):
            return self.host
        return self.host[:-6]

    def _get(self, path):
        resp = requests.get(self._base_host + path, **self._requests_args())
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, files, headers=None):
        resp = requests.post(
            self._base_host + path,
            files=files,
            **self._requests_args(headers=headers)
        )
        logger.info(f'_post: url={self._base_host + path}, status={resp.status_code}, response={resp.content}')
        if resp.status_code == 400:
            error_reason = resp.json()
            error_type = error_reason.get('@type', 'Unknown')
            error_message = error_reason.get('error', 'Unknown')
            raise HTTPError(f'Bad Request for URL: {self._base_host + path}: type={error_type}, message={error_message}')
        resp.raise_for_status()
        return resp.json()

    def _requests_args(self, headers=None):
        if self.token is not None:
            headers = headers.copy() if headers is not None else {}
            token = self.token.decode('utf8') if isinstance(self.token, bytes) else self.token
            headers['Authorization'] = 'Bearer ' + token
            return {'headers': headers}
        elif headers is not None:
            return {'auth': (self.username, self.password), 'headers': headers}
        else:
            return {'auth': (self.username, self.password)}


class Index(object):
    """
    WEKO Index
    """
    client = None
    raw = None
    parent = None

    def __init__(self, client, desc, parent=None):
        self.client = client
        self.parent = parent
        self.raw = desc

    @property
    def title(self):
        return self.raw['name']

    @property
    def identifier(self):
        return self.raw['id']

    @property
    def children(self):
        return [Index(self.client, i, parent=self) for i in self.raw['children']]

    def get_items(self):
        root = self.client._get(f'api/index/?search_type=2&q={self.identifier}')
        logger.debug(f'get_items: {root}')
        items = []
        for entry in root['hits']['hits']:
            logger.debug(f'get_item: {entry}')
            items.append(Item(entry))
        return items

    def get_item_by_id(self, item_id):
        root = self.client._get(f'api/records/{item_id}')
        logger.debug(f'get_item: {root}')
        return Item(root)


class Item(object):
    """
    WEKO Item
    """
    raw = None
    index = None

    def __init__(self, desc, index=None):
        self.raw = desc
        self.index = index

    @property
    def identifier(self):
        return self.raw['id']

    @property
    def primary_title(self):
        v = self._metadata['title']
        if isinstance(v, str):
            return v
        return v[0]

    @property
    def title(self):
        return self._metadata['title']

    @property
    def updated(self):
        return self._metadata['updated']

    @property
    def _metadata(self):
        metadata = self.raw['metadata']
        if '_item_metadata' in metadata:
            return metadata['_item_metadata']
        return metadata

    @property
    def files(self):
        file_items = [k
                      for k, v in self._metadata.items()
                      if k.startswith('item_') and 'attribute_type' in v and v['attribute_type'] == 'file']
        return [File(file_item) for file_item in self._metadata[file_items[0]]['attribute_value_mlt']]


class File(object):
    """
    WEKO File
    """
    raw = None
    item = None

    def __init__(self, desc, item=None):
        self.raw = desc
        self.item = item

    @property
    def filename(self):
        return self.raw['filename']

    @property
    def format(self):
        if 'format' not in self.raw:
            return None
        return self.raw['format']

    @property
    def version_id(self):
        return self.raw['version_id']

    @property
    def download_url(self):
        return self.raw['url']['url']
