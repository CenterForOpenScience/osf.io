import requests
import mimetypes

from framework.exceptions import HTTPError


def is_indexed(filename):
    INDEXED_TYPES = [
        'text/plain',
    ]
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and mime_type in INDEXED_TYPES


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


def collect_files_from_addon(addon, tree):
    """ Generate the file dicts for all files in an addon.

    :param addon: the addon objct
    :param tree: the addons file tree as a dict.
    :return: generator returning file dicts.
    """
    children = tree['children']
    for child in children:
        if child.get('children'):
            for file_ in collect_files_from_addon(addon, child):
                yield file_
        else:
            path, name = child['path'], child['name']
            if is_indexed(name):
                file_, created = addon.find_or_create_file_guid(path)
                content = get_content_of_file_from_addon(file_, addon)
                yield {'name': name, 'content': content, 'path': path}


def collect_files(node):
    """ Generate the contents of a projects.

    :param node: project.
    :return: Genarator returning file dicts.
    """
    addons = node.get_addons()
    for addon in addons:
        try:
            file_tree = addon._get_file_tree()
        except (AttributeError, HTTPError):
            continue
        for file_ in collect_files_from_addon(addon, file_tree):
            yield file_
