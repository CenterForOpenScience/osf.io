import requests

def collect_files(node):
    """ Generate the contents of a projects.
    :param node: node
    :return: dict with the files name and it's contents.
    """

    # TODO: Generalize to other addons
    osf_addon = node.get_addon('osfstorage')
    node_children = osf_addon._get_file_tree()['children']
    for child in node_children:
        path, name = child['path'], child['name']
        file_, created = osf_addon.find_or_create_file_guid(path)
        # download count not incremented when rendering.
        resp = requests.get(file_.download_url + '&mode=render')
        response = unicode(resp.text).encode('utf-8')
        yield {'name': name, 'content': response}
