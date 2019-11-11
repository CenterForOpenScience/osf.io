import requests
import os
import argparse
import logging
import time
from zipfile import ZipFile

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument(
    '-g',
    '--guid',
    help='This is the GUID of the target node on the OSF'
)
parser.add_argument(
    '-d',
    '--directory',
    help='This is the target Directory for the project and its files'
)
parser.add_argument(
    '-t',
    '--token',
    help='This is the bearer token for auth. This is required'
)
parser.add_argument(
    '-u',
    '--url',
    help='Base URL for OSF API.'
)

BASE_URL = 'https://files.osf.io/'

def consume_files(guid, token, directory, base_url=BASE_URL):

    zip_url = '{}v1/resources/{}/providers/osfstorage/?zip='.format(base_url, guid)
    path = os.path.join(directory,guid)
    os.mkdir(path)
    path = os.path.join(path,'files')
    os.mkdir(path)
    if token:
        auth_header = {'Authorization': 'Bearer {}'.format(token)}
    else:
        auth_header = {}

    try:
        response = requests.get(zip_url.format(guid), headers=auth_header)
        if response.status_code == 429:
            keep_trying = retry
            response_headers = response.headers
            wait_time = response_headers['Retry-After']
            if keep_trying:
                logging.log(logging.INFO, 'Throttled: retrying in {wait_time}s')
                time.sleep(int(wait_time))
            else:
                logging.log(logging.ERROR, 'Throttled. Please retry after {wait_time}s')
        elif response.status_code >= 400:
            status_code = response.status_code
            content = getattr(response, 'content', None)
            raise requests.exceptions.HTTPError(
                'Status code {}. {}'.format(status_code, content))
    except requests.exceptions.RequestException as e:
        logging.log(logging.ERROR,'HTTP Request failed: {}'.format(e))
        raise

    zipfile_location = os.path.join(path, (guid+'.zip'))
    with open(zipfile_location, 'wb') as file:
        file.write(response.content)

    with ZipFile(zipfile_location, 'r') as zipObj:
        zipObj.extractall(path)

    os.remove(zipfile_location)
    print('File data successfully transferred!')

def main(default_args=True):
    if (default_args):
        args = parser.parse_args(['--guid', 'default', '--directory', 'default'])
    else:
        args = parser.parse_args()
    args = parser.parse_args()
    guid = args.guid
    directory = args.directory
    token = args.token
    url = args.url

    if not guid:
        raise ValueError('Project GUID must be specified! Use -g')
    if not directory:
        # Setting default to current directory
        directory = '.'
    if not url:
        url = BASE_URL

    consume_files(guid, token, directory, url)



if __name__ == '__main__':

    main(default_args=False)