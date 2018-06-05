import logging
import requests
from io import BytesIO
from lxml import etree
import os
import datetime
import mimetypes
import httplib as http
from framework.exceptions import HTTPError
from requests.exceptions import ConnectionError

logger = logging.getLogger('addons.weko.client')

APP_NAMESPACE = 'http://www.w3.org/2007/app'
ATOM_NAMESPACE = 'http://www.w3.org/2005/Atom'
RDF_NAMESPACE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
DC_NAMESPACE = 'http://purl.org/metadata/dublin_core#'


class UnauthorizedError(IOError):
    pass


class Index(object):
    raw = None
    parentIdentifier = None

    def __init__(self, title=None, index_id=None, about=None):
        self.raw = {'title': title, 'id': index_id, 'about': about}

    @property
    def nested(self):
        title = self.raw['title']
        nested = 0
        while title.startswith('--'):
            nested += 1
            title = title[2:]
        return nested

    @property
    def title(self):
        return self.raw['title'][self.nested * 2:]

    @property
    def identifier(self):
        return self.raw['id']

    @property
    def about(self):
        return self.raw['about']


class Connection(object):
    host = None
    token = None
    username = None
    password = None

    def __init__(self, host, token=None, username=None, password=None):
        self.host = host
        self.token = token
        self.username = username
        self.password = password

    def get_login_user(self, default_user=None):
        resp = requests.get(self.host + 'servicedocument.php',
                            **self._requests_args())
        if resp.status_code != 200:
            resp.raise_for_status()
        if self.username is not None:
            default_user = self.username
        return resp.headers.get('X-WEKO-Login-User', default_user)

    def get(self, path):
        resp = requests.get(self.host + path, **self._requests_args())
        if resp.status_code != 200:
            resp.raise_for_status()
        tree = etree.parse(BytesIO(resp.content))
        return tree

    def get_url(self, url):
        resp = requests.get(url, **self._requests_args())
        if resp.status_code != 200:
            resp.raise_for_status()
        tree = etree.parse(BytesIO(resp.content))
        return tree

    def delete_url(self, url):
        resp = requests.delete(url, **self._requests_args())
        if resp.status_code != 200:
            resp.raise_for_status()

    def post_url(self, url, stream, default_headers=None):
        resp = requests.post(url, data=stream,
                             **self._requests_args(default_headers))
        if resp.status_code != 200:
            resp.raise_for_status()
        tree = etree.parse(BytesIO(resp.content))
        return tree

    def _requests_args(self, headers=None):
        if self.token is not None:
            headers = headers.copy() if headers is not None else {}
            headers['Authorization'] = 'Bearer ' + self.token
            return {'headers': headers}
        elif headers is not None:
            return {'auth': (self.username, self.password), 'headers': headers}
        else:
            return {'auth': (self.username, self.password)}


def parse_index(desc):
    return Index(title=desc.find('{%s}title' % DC_NAMESPACE).text,
                 index_id=desc.find('{%s}identifier' % DC_NAMESPACE).text,
                 about=desc.attrib['{%s}about' % RDF_NAMESPACE])

def connect(sword_url, token=None, username=None, password=None):
    try:
        return Connection(sword_url, token=token,
                          username=username, password=password)
    except ConnectionError:
        return None


def connect_from_settings(weko_settings, node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    from addons.weko.provider import WEKOProvider
    provider = WEKOProvider(node_settings.external_account)

    if provider.repoid is not None:
        return connect(provider.sword_url, token=provider.token)
    else:
        return connect(provider.sword_url, username=provider.userid,
                       password=provider.password)


def connect_or_error(sword_url, token=None, username=None, password=None):
    try:
        return Connection(sword_url, token=token,
                          username=username, password=password)
    except UnauthorizedError:
        raise HTTPError(http.UNAUTHORIZED)


def connect_from_settings_or_401(weko_settings, node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    from addons.weko.provider import WEKOProvider
    provider = WEKOProvider(node_settings.external_account)

    if provider.repoid is not None:
        return connect_or_error(provider.sword_url, token=provider.token)
    else:
        return connect_or_error(provider.sword_url, username=provider.userid,
                                password=provider.password)


def get_all_indices(connection):
    root = connection.get('servicedocument.php')
    indices = []
    for desc in root.findall('.//{%s}Description' % RDF_NAMESPACE):
        indices.append(parse_index(desc))

    ids = []
    for index in indices:
        if index.nested > 0:
            index.parentIdentifier = ids[index.nested - 1]

        if len(ids) == index.nested + 1:
            ids[index.nested] = index.identifier
        elif len(ids) > index.nested + 1:
            ids = ids[0:index.nested + 1]
            ids[index.nested] = index.identifier
        else:
            ids.append(index.identifier)
    return indices


def get_index_by_id(connection, index_id):
    return list(filter(lambda i: i.identifier == index_id, get_all_indices(connection)))[0]

def get_serviceitemtype(connection):
    root = connection.get('serviceitemtype.php')
    logger.debug('Serviceitemtype: {}'.format(etree.tostring(root)))
    r = {'metadata': [], 'item_type': []}
    for metadata in root.findall('metadata'):
        for k in filter(lambda k: k.startswith('columnname_'),
                        metadata.attrib.keys()):
            r['metadata'].append({'column_id': k[11:],
                                  'column_name': metadata.attrib[k]})
    for item_types_elem in root.findall('itemTypes'):
        for item_type_elem in item_types_elem.findall('itemType'):
            item_type = {'mapping_info': item_type_elem.attrib['mapping_info'],
                         'name': item_type_elem.find('name').text,
                         'basic_attributes': [],
                         'additional_attributes': []}
            basic_attributes_elem = item_type_elem.find('basicAttributes')
            if basic_attributes_elem is not None:
                for attr_elem in basic_attributes_elem:
                    columns = []
                    for k in filter(lambda k: k.startswith('columnname_'),
                                    attr_elem.attrib.keys()):
                        columns.append({'column_id': k[11:],
                                        'column_name': attr_elem.attrib[k]})
                    item_type['basic_attributes'].append({'type': attr_elem.tag,
                                                          'columns': columns})
            for additional_attr_elem in item_type_elem.findall('.//additionalAttribute'):
                columns = []
                additional_attr = {'name': additional_attr_elem.find('name').text}
                for k in additional_attr_elem.attrib.keys():
                    if k.startswith('columnname_'):
                        columns.append({'column_id': k[11:],
                                        'column_name': additional_attr_elem.attrib[k]})
                    else:
                        additional_attr[k] = additional_attr_elem.attrib[k]
                if additional_attr_elem.find('candidates') is not None:
                    additional_attr['candidates'] = additional_attr_elem.find('candidates').text.split(additional_attr['delimiters'])
                item_type['additional_attributes'].append(additional_attr)
            r['item_type'].append(item_type)
    return r

def delete(connection, url):
    connection.delete_url(url)

def post(connection, insert_index_id, stream, stream_size):
    root = connection.get('servicedocument.php')
    target = None
    for collection in root.findall('.//{%s}collection' % APP_NAMESPACE):
        target = collection.attrib['href']
    logger.info('Post: {} on {}'.format(insert_index_id, target))
    weko_headers = {
        'Content-Disposition': 'filename=temp.zip',
        'Content-Type': 'application/zip',
        'Packaging': 'http://purl.org/net/sword/package/SimpleZip',
        'Content-Length': str(stream_size),
        'insert_index': str(insert_index_id)
    }
    resp = connection.post_url(target, stream, headers=weko_headers)
    logger.info(etree.tostring(resp))
    for index, elem in enumerate(resp.findall('.//{%s}content' % ATOM_NAMESPACE)):
        src = elem.attrib['src']
        logger.info(src)
        if 'message' in elem.attrib:
            logger.warn('{}: {}'.format(index + 1, elem.attrib['message']))
    return src

def create_index(connection, title_ja=None, title_en=None, relation=None):
    root = connection.get('servicedocument.php')
    indices = []
    for desc in root.findall('.//{%s}Description' % RDF_NAMESPACE):
        indices.append(parse_index(desc))
    index_id = max(map(lambda i: int(i.identifier), indices)) + 1

    target = None
    for collection in root.findall('.//{%s}collection' % APP_NAMESPACE):
        target = collection.attrib['href']
    logger.info('Create: {} on {}'.format(index_id, target))
    post_xml = etree.Element('{%s}RDF' % RDF_NAMESPACE,
                             nsmap={'rdf': RDF_NAMESPACE, 'dc': DC_NAMESPACE})
    desc_elem = etree.SubElement(post_xml, '{%s}Description' % RDF_NAMESPACE)
    id_elem = etree.SubElement(desc_elem, '{%s}identifier' % DC_NAMESPACE)
    id_elem.text = str(index_id)
    if title_ja is not None:
        title_elem = etree.SubElement(desc_elem, '{%s}title' % DC_NAMESPACE)
        title_elem.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'ja'
        title_elem.text = title_ja
    if title_en is not None:
        title_elem = etree.SubElement(desc_elem, '{%s}title' % DC_NAMESPACE)
        title_elem.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en'
        title_elem.text = title_en
    if relation is not None:
        rel_elem = etree.SubElement(desc_elem, '{%s}relation' % DC_NAMESPACE)
        rel_elem.text = relation
    logger.debug('XML: {}'.format(etree.tostring(post_xml)))
    stream = etree.tostring(post_xml, encoding='UTF-8', xml_declaration=True)
    weko_headers = {
        'Content-Disposition': 'filename=tree.xml',
        'Content-Type': 'text/xml',
        'Content-Length': str(len(stream)),
    }
    root = connection.post_url(target, stream, headers=weko_headers)
    logger.info('Result: {}'.format(etree.tostring(root)))
    return index_id

def update_index(connection, index_id, title_ja=None, title_en=None, relation=None):
    root = connection.get('servicedocument.php')
    target = None
    for collection in root.findall('.//{%s}collection' % APP_NAMESPACE):
        target = collection.attrib['href']
    logger.info('Update: {} on {}'.format(index_id, target))
    post_xml = etree.Element('{%s}RDF' % RDF_NAMESPACE,
                             nsmap={'rdf': RDF_NAMESPACE, 'dc': DC_NAMESPACE})
    desc_elem = etree.SubElement(post_xml, '{%s}Description' % RDF_NAMESPACE)
    source_elem = etree.SubElement(desc_elem, '{%s}source' % DC_NAMESPACE)
    source_elem.text = index_id
    if title_ja is not None:
        title_elem = etree.SubElement(desc_elem, '{%s}title' % DC_NAMESPACE)
        title_elem.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'ja'
        title_elem.text = title_ja
    if title_en is not None:
        title_elem = etree.SubElement(desc_elem, '{%s}title' % DC_NAMESPACE)
        title_elem.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en'
        title_elem.text = title_en
    if relation is not None:
        rel_elem = etree.SubElement(desc_elem, '{%s}relation' % DC_NAMESPACE)
        rel_elem.text = relation
    logger.debug('XML: {}'.format(etree.tostring(post_xml)))
    stream = etree.tostring(post_xml, encoding='UTF-8', xml_declaration=True)
    weko_headers = {
        'Content-Disposition': 'filename=tree.xml',
        'Content-Type': 'text/xml',
        'Content-Length': str(len(stream)),
    }
    root = connection.post_url(target, stream, headers=weko_headers)
    logger.info('Result: {}'.format(etree.tostring(root)))

def create_import_xml(item_type, internal_item_type_id, uploaded_filenames, title, title_en, contributors):
    post_xml = etree.Element('export')
    item_elem = etree.SubElement(post_xml, 'repository_item')
    item_elem.attrib['item_id'] = '1'
    item_elem.attrib['item_no'] = '1'
    item_elem.attrib['revision_no'] = '0'
    item_elem.attrib['prev_revision_no'] = '0'
    item_elem.attrib['item_type_id'] = str(internal_item_type_id)
    item_elem.attrib['title'] = title
    item_elem.attrib['title_english'] = title_en
    item_elem.attrib['language'] = 'ja'
    item_elem.attrib['review_status'] = '0'
    item_elem.attrib['review_date'] = ''
    item_elem.attrib['shown_status'] = '1'
    item_elem.attrib['shown_date'] = datetime.datetime.now().strftime('%Y-%m-%d')

    item_elem.attrib['reject_status'] = '0'
    item_elem.attrib['reject_date'] = ''
    item_elem.attrib['reject_reason'] = ''
    item_elem.attrib['search_key'] = ''
    item_elem.attrib['search_key_english'] = ''
    item_elem.attrib['remark'] = ''

    item_type_elem = etree.SubElement(post_xml, 'repository_item_type')
    item_type_elem.attrib['item_type_id'] = str(internal_item_type_id)
    item_type_elem.attrib['item_type_name'] = item_type['name']
    item_type_elem.attrib['item_type_short_name'] = item_type['name']
    item_type_elem.attrib['mapping_info'] = item_type['mapping_info']
    item_type_elem.attrib['explanation'] = 'default item type'

    for index, item_attr_type in enumerate(item_type['additional_attributes']):
        item_attr_type_elem = etree.SubElement(post_xml, 'repository_item_attr_type')
        item_attr_type_elem.attrib['item_type_id'] = str(internal_item_type_id)
        item_attr_type_elem.attrib['attribute_id'] = str(index + 1)
        item_attr_type_elem.attrib['show_order'] = str(index + 1)
        item_attr_type_elem.attrib['attribute_name'] = item_attr_type['name']
        item_attr_type_elem.attrib['attribute_short_name'] = item_attr_type['name']
        item_attr_type_elem.attrib['input_type'] = _get_export_type(item_attr_type['type'])
        item_attr_type_elem.attrib['is_required'] = '1' if item_attr_type['required'] == 'true' else '0'
        item_attr_type_elem.attrib['plural_enable'] = '1' if item_attr_type['allowmultipleinput'] == 'true' else '0'
        item_attr_type_elem.attrib['line_feed_enable'] = '1' if item_attr_type['specifynewline'] == 'true' else '0'
        item_attr_type_elem.attrib['list_view_enable'] = '1' if item_attr_type['listing'] == 'true' else '0'
        item_attr_type_elem.attrib['hidden'] = '1' if item_attr_type['hidden'] == 'true' else '0'
        for k in filter(lambda k: k.endswith('_mapping') or k == 'display_lang_type', item_attr_type.keys()):
            item_attr_type_elem.attrib[k] = item_attr_type[k]

        if item_attr_type['type'] == 'file' and item_attr_type['junii2_mapping'] == 'fullTextURL':
            for i, uploaded_filename in enumerate(uploaded_filenames):
                file_elem = etree.SubElement(post_xml, 'repository_file')
                file_elem.attrib['item_type_id'] = str(internal_item_type_id)
                file_elem.attrib['attribute_id'] = str(index + 1)
                file_elem.attrib['item_no'] = '1'
                file_elem.attrib['file_no'] = str(i + 1)
                file_elem.attrib['file_name'] = uploaded_filename
                filename_body, filename_ext = os.path.splitext(uploaded_filename)
                file_elem.attrib['display_name'] = filename_body
                file_elem.attrib['display_type'] = '0'
                mime_type = mimetypes.guess_type(uploaded_filename)[0]
                file_elem.attrib['mime_type'] = mime_type if mime_type is not None else 'application/octet-stream'
                file_elem.attrib['extension'] = filename_ext
                file_elem.attrib['license_id'] = '0'
                file_elem.attrib['license_notation'] = ''
                file_elem.attrib['pub_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
                file_elem.attrib['item_id'] = '1'
                file_elem.attrib['browsing_flag'] = '0'
                file_elem.attrib['cover_created_flag'] = '0'

                license_elem = etree.SubElement(post_xml, 'repository_license_master')
                license_elem.attrib['license_id'] = '0'
                license_elem.attrib['license_notation'] = ''
        elif item_attr_type['type'] == 'name' and item_attr_type['junii2_mapping'] == 'creator':
            for name_index, contributor in enumerate(contributors):
                logger.info('Contributor: {}'.format(contributor))
                name_elem = etree.SubElement(post_xml, 'repository_personal_name')
                name_elem.attrib['item_type_id'] = str(internal_item_type_id)
                name_elem.attrib['attribute_id'] = str(index + 1)
                name_elem.attrib['item_no'] = '1'
                name_elem.attrib['personal_name_no'] = str(name_index + 1)
                name_elem.attrib['author_id'] = str(name_index + 1)
                name_elem.attrib['family'] = contributor['family']
                name_elem.attrib['family_ruby'] = contributor['family']
                name_elem.attrib['name'] = contributor['name']
                name_elem.attrib['name_ruby'] = contributor['name']
                name_elem.attrib['e_mail_address'] = ''
                name_elem.attrib['prefix_name'] = ''
                name_elem.attrib['suffix'] = ''
                name_elem.attrib['item_id'] = '1'

        if 'candidates' in item_attr_type:
            for cand_no, candidate in enumerate(item_attr_type['candidates']):
                item_attr_cand_elem = etree.SubElement(post_xml, 'repository_item_attr_candidate')
                item_attr_cand_elem.attrib['item_type_id'] = str(internal_item_type_id)
                item_attr_cand_elem.attrib['attribute_id'] = str(index + 1)
                item_attr_cand_elem.attrib['candidate_no'] = str(cand_no + 1)
                item_attr_cand_elem.attrib['candidate_value'] = candidate
                item_attr_cand_elem.attrib['candidate_short_value'] = candidate

    return post_xml

def _get_export_type(serviceitemtype_type):
    if serviceitemtype_type == 'pulldownmenu':
        return 'select'
    if serviceitemtype_type == 'biblioinfo':
        return 'biblio_info'
    return serviceitemtype_type
