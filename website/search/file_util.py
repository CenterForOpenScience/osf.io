import requests

from framework.exceptions import HTTPError


INDEXED_TYPES = [
    'txt',
    'md',
    'rtf',
    'docx',
    'pdf',
]


def is_indexed(filename):
    extension = filename.rsplit('.')[-1]
    indexed = extension in INDEXED_TYPES
    return indexed


def get_content_of_file(file_):
    url = file_.mfr_public_download_url
    response = requests.get(url)
    content = response.content
    return content


def build_file_document(name, path, addon, include_content=True):
    file_, created = addon.find_or_create_file_guid(path)
    parent_id = file_.node._id
    file_content = None
    if include_content:
        file_content = get_content_of_file(file_)
    return {
        'name': name,
        'path': path,
        'content': file_content,
        'parent_id': parent_id,
    }


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
            if is_indexed(name):
                yield {'name': name, 'path': path, 'addon': addon}


def collect_files(node):
    """ Generate the contents of a projects.

    :param node: project.
    :return: Genarator returning file dicts.
    """
    addons = node.get_addons()
    for addon in addons:
        try:
            for file_dict in collect_files_from_addon(addon):
                yield file_dict
        except (AttributeError, HTTPError):
            continue
