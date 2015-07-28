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


def is_indexed(filename):
def is_indexed(filename, addon):
    if not addon.config.short_name == 'osfstorage':
        return False
    return filename.rsplit('.')[-1] in INDEXED_TYPES


def get_file_content(file_):
    url = file_.download_url + '&mode=render'
    response = requests.get(url)
    return response.content


def build_file_document(name, path, addon, include_content=True):
    """Return file data to be in the indexed document as a dict.

    :param name: Name of file.
    :param path: Path of file.
    :param addon: Instance of storage addon containing the containing the file.
    :param include_content: Include the content of the file in document.
    """
    file_, created = addon.find_or_create_file_guid(path)
    parent_id = file_.node._id
    file_content = get_file_content(file_) if include_content else None
    return {
        'id': file_.node._id,
        'name': name,
        'path': path,
        'content': file_content,
        'parent_id': parent_id,
    }


#TODO: Restrict to osfstorage
def collect_files_from_addon(addon, tree=None):
    """ Generate the file dicts for all files in an addon.

    :param addon: the addon objct
    :param tree: the addons file tree as a dict.
    :return: generator returning file dicts.
    """
    tree = tree or addon._get_file_tree()
    children = tree['children']
    for child in children:
        if child.get('children'):
            for file_ in collect_files_from_addon(addon, child):
                yield file_
        else:
            path, name = child['path'], child['name']
            if is_indexed(name, addon):
                yield {'name': name, 'path': path, 'addon': addon}


def collect_files(node):
    """ Generate the file_dicts of files in osfstorage.

    :param node: project.
    :return: Genarator returning file dicts consisting of name, path, addon.
    """
    addons = node.get_addons()
    for addon in addons:
        if addon.config.short_name == 'osfstorage':
            try:
                for file_dict in collect_files_from_addon(addon):
                    yield file_dict
            except (AttributeError, HTTPError):
                continue
