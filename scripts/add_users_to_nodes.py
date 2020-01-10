import csv
import logging
import requests
import argparse
from website import settings
from io import BytesIO

from website.app import setup_django
setup_django()

logger = logging.getLogger(__name__)


def add_contributor(node_guid, token, contrib_guid, dry_run=False):
    payload = {
        'data': {
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'admin',
            },
            'relationships': {
                'users': {
                    'data': {
                        'type': 'users',
                        'id': contrib_guid
                    }
                }
            }
        }
    }
    if not dry_run:
        resp = requests.post(
            '{}v2/nodes/{}/contributors/?send_email=false'.format(settings.API_DOMAIN, node_guid),
            json=payload,
            headers={'Authorization': 'Bearer {}'.format(token)}
        )

        if resp.status_code == 400 and 'is already a contributor.' in resp.json()['errors'][0]['detail']:
            return

        resp.raise_for_status()
    logger.info('User {} added to node {} dry run={}'.format(contrib_guid, node_guid, dry_run))


def get_file_from_guid(token, guid, filename):
    headers = {'Authorization': 'Bearer {}'.format(token)}

    resp = requests.get('{}v2/nodes/{}/files/osfstorage/'.format(settings.API_DOMAIN, guid).replace('localhost', '192.168.168.167'), headers=headers)
    resp.raise_for_status()

    json = resp.json()['data']

    try:
        download_link = next(x['links']['upload'] for x in json if x['attributes']['name'] == filename)
    except StopIteration:
        raise Exception('\'{}\' not found'.format(filename))

    resp = requests.get(download_link, headers=headers)

    return BytesIO(resp.content)


def main(token, guid, filename, dry_run=False):
    group1 = ['ytu9p', 'alh38']
    group2 = ['pnyji', 'd5mks', 't8b9p', 'sy6ch', 'qtvkn', 'gjsf9', '6gmyt']

    tsv_data = get_file_from_guid(token, guid, filename)
    reader = csv.DictReader(tsv_data, delimiter='\t')
    for row in reader:
        if row['component_type'] == 'umbrella_project':
            for contrib_guid in group1 + group2:
                add_contributor(row['osf_guid'], token, contrib_guid=contrib_guid, dry_run=dry_run)
        else:
            for contrib_guid in group2:
                add_contributor(row['osf_guid'], token, contrib_guid=contrib_guid, dry_run=dry_run)


if __name__ == '__main__':
    # initiate the parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--token',
        '-t',
        type=str,
        action='store',
        dest='token',
        required=True,
        help='token for nodes which contributors are being added to.',
    )
    parser.add_argument(
        '--dry_run',
        type=bool,
        default=False,
        help='Makes this is a dry_run with no new contributors added.',
    )
    parser.add_argument(
        '--guid',
        '-g',
        type=str,
        action='store',
        dest='guid',
        required=True,
        help='The guid of the project that has the tsv in it',
    )
    parser.add_argument(
        '--filename',
        '-f',
        type=str,
        action='store',
        dest='filename',
        required=True,
        help='The filename of the tsv',
    )
    args = parser.parse_args()
    token = args.token
    dry_run = args.dry_run
    guid = args.guid
    filename = args.filename
    main(token, guid, filename, dry_run=dry_run)
