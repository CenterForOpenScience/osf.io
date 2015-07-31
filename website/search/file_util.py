import logging
import requests

from framework.exceptions import HTTPError
from website import settings


INDEXED_TYPES = [
    'txt',
    'md',
    'rtf',
    'docx',
    'pdf',
]


def file_indexing(func):
    """Execute function only if use_file_indexing setting is true.
    """
    def wrapper(*args, **kwargs):
        if settings.USE_FILE_INDEXING:
            return func(*args, **kwargs)
    return wrapper


def is_indexed(filename, addon):
    if not addon.config.short_name == 'osfstorage':
        return False

    return filename.rsplit('.')[-1] in INDEXED_TYPES


def get_file_content(file_):
    url = file_.download_url + '&mode=render'
    response = requests.get(url)
    return response.content


def norm_path(path):
    return path if not path[0] == '/' else path[1:]


def build_file_document(file_node, include_content=True):
    """Return file data to be in the indexed document as a dict.

    :param name: Name of file.
    :param path: Path of file.
    :param addon: Instance of storage addon containing the containing the file.
    :param include_content: Include the content of the file in document.
    """
    name = file_node.name
    parent_node = file_node.node
    parent_id = parent_node._id
    path = norm_path(file_node.path)
    addon = file_node.node_settings

    file_, created = addon.find_or_create_file_guid(path)
    file_.enrich()
    file_content = get_file_content(file_) if include_content else None
    file_size = file_.size

    return {
        'name': name,
        'path': path,
        'content': file_content,
        'parent_id': parent_id,
        'size': file_size,
    }


def collect_files_from_filenode(file_node):
    logging.info('NODE: {}'.format(repr(file_node)))
    children = [] if file_node.is_file else file_node.children
    if file_node.is_file:
        yield file_node

    for child in children:
        if file_node.is_folder:
            for file_ in collect_files_from_filenode(child):
                yield file_
        elif file_node.is_file:
            yield file_node


def collect_files(node):
    osf_addon = node.get_addon('osfstorage')
    root_node = osf_addon.root_node
    for file_dict in collect_files_from_filenode(root_node):
        yield file_dict
