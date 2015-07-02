from framework.exceptions import HTTPError
import requests


def collect_from_addon(addon, tree):
    addon_name = addon.config.short_name
    children = tree['children']
    for child in children:
        if child.get('children'):
            for file_ in collect_from_addon(addon, child):
                yield file_
        else:
            path, name = child['path'], child['name']
            file_, created = addon.find_or_create_file_guid(path)
            download_url = file_.download_url
            download_url += '&mode=render' if addon_name == 'osfstorage' else ''
            response = requests.get(download_url)
            content = unicode(response.text).encode('utf-8')
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
