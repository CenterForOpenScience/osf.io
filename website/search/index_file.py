import requests


def collect_from_osfstorage(addon, tree):
    children = tree['children']
    for child in children:
        path, name = child['path'], child['name']
        file_, created = addon.find_or_create_file_guid(path)
        response = requests.get(file_.download_url + '&mode=render')
        content = unicode(response.text).encode('utf-8')
        yield {'name': name, 'content': content}


def collect_from_github(addon, tree):
    children = tree['children']
    for child in children:
        if child.get('children'):
            for file_ in collect_from_github(addon, child):
                yield file_
        else:
            path, name = child['path'], child['name']
            file_, created = addon.find_or_create_file_guid(path)
            response = requests.get(file_.download_url)
            content = unicode(response.text).encode('utf-8')
            yield {'name': name, 'content': content}


def collect_files(node):
    """ Generate the contents of a projects.
    :param node: node
    :return: dict with the files name and it's contents.
    """

    # TODO: Generalize to other addons
    addons = node.get_addons()
    for addon in addons:
        addon_name = addon.config.short_name
        logging.info('ADDON : {}\n'.format(addon_name))
        try:
            file_tree = addon._get_file_tree()
        except AttributeError:
            continue

        if addon_name == 'osfstorage':
            for file_ in collect_from_osfstorage(addon, file_tree):
                logging.info('File from {}:\n {}\n'.format(addon_name, pformat(file_)))
                yield file_

        elif addon_name == 'github':
            for file_ in collect_from_github(addon, file_tree):
                yield file_
