import requests
import mimetypes

from framework.exceptions import HTTPError


def is_indexed(filename):
    INDEXED_TYPES = [
        'text/plain',
    ]
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and mime_type in INDEXED_TYPES


def get_content_of_file_from_addon(file_, render):
    url = file_.download_url
    if render:
        url += '&mode=render'
    response = requests.get(url)
    content = unicode(response.text).encode('utf-8')
    return content


def collect_from_addon(addon, tree):
    addon_name = addon.config.short_name
    children = tree['children']
    for child in children:
        if child.get('children'):
            for file_ in collect_from_addon(addon, child):
                yield file_
        else:
            path, name = child['path'], child['name']
            if is_indexed(name):
                file_, created = addon.find_or_create_file_guid(path)
                to_render = addon_name == 'osfstorage'
                content = get_content_of_file_from_addon(file_, render=to_render)
                yield {'name': name, 'content': content}


def collect_files(node):
    """ Generate the contents of a projects.
    :param node: node
    :return: dict with the files name and it's contents.
    """
    addons = node.get_addons()
    for addon in addons:
        try:
            file_tree = addon._get_file_tree()
        except (AttributeError, HTTPError):
            continue
        for file_ in collect_from_addon(addon, file_tree):
            yield file_
