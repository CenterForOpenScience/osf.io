from website.settings import API_DOMAIN
import requests
import pprint


def build_api_call(pid):
    """ Build a call to api v2 for the projects list of files.
    """
    path = ['v2']
    path.append('nodes')
    path.append(pid)
    path.append('files')
    end_part = '?path=%2F&provider=osfstorage'
    url = API_DOMAIN + '/'.join(path) + end_part
    return url


def get_files_for(pid):
    """ Return the contents of a projects files.
    :param pid: project id
    :return: list of unicode strings.
    """
    url = build_api_call(pid)
    print(url)
    resp = requests.get(url).json()
    print(pprint.pprint(resp))

    file_contents = []
    for file in resp['data']:
        file_link = file['links']['self']
        print(file_link)
        file_resp = requests.get(file_link)
        content = file_resp.text
        file_contents.append(content)
    print('FILES: {}'.format(len(file_contents)))
    if file_contents:
        print(u'SIZE OF ONE: {}'.format(len(file_contents[0])))