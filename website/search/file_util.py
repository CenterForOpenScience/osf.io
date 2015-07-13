import requests
import mimetypes

from framework.exceptions import HTTPError


INDEXED_TYPES = [
        'text/plain',
    ]

def is_indexed(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and mime_type in INDEXED_TYPES


def build_file_document(name, path, addon):
    file_, created = addon.find_or_create_file_guid(path)
    parent_id = file_.node._id
    content = get_content_of_file_from_addon(file_, addon)
    return {
        'name': name,
        'path': path,
        'content': content,
        'parent_id': parent_id,
    }


def get_content_of_file_from_addon(file_, addon):
    """ Return the contents of a file as a string.

    :param file_: A GuidFile object.
    :param addon: The addon object containing the file.
    :return: string.
    """
    url = file_.download_url
    if addon.config.short_name in ('osfstorage',):
        url += '&mode=render'
    response = requests.get(url)
    content = unicode(response.text).encode('utf-8')
    return content


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
                yield build_file_document(name, path, addon)


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
