import os
import argparse
import datetime
import requests
from datacite import schema40
DOI_FORMAT = '{prefix}/osf.io/{guid}'
BASE_URL = 'http://localhost:8000/'

PREPRINT_DOI_NAMESPACE = {
    'osf': '10.31219',
    'agrixiv': '10.31220',
    'arabixiv': '10.31221',
    'bitss': '10.31222',
    'eartharxiv': '10.31223',
    'engrxiv': '10.31224',
    'focusarchive': '10.31225',
    'frenxiv': '10.31226',
    'inarxiv': '10.31227',
    'lawarxiv': '10.31228',
    'lissa': '10.31229',
    'marxiv': '10.31230',
    'mindrxiv': '10.31231',
    'nutrixiv': '10.31232',
    'paleorxiv': '10.31233',
    'psyarxiv': '10.31234',
    'socarxiv': '10.31235',
    'sportrxiv': '10.31236',
    'thesiscommons': '10.31237',
    'ecsarxiv': '10.1149',
    'africarxiv': '10.31730'

}


def build_doi(data):
    provider_id = data['embeds']['provider']['data']['id']
    return DOI_FORMAT.format(prefix=PREPRINT_DOI_NAMESPACE[provider_id], guid=data['id'])


def build_metadata(node):
    """Return the formatted datacite metadata XML as a string.
     """

    users = node['embeds']['contributors']['data']

    data = {
        'identifier': {
            'identifier': build_doi(node),
            'identifierType': 'DOI',
        },
        'creators': [
            {'creatorName': user['embeds']['users']['data']['attributes']['full_name'],
             'givenName': user['embeds']['users']['data']['attributes']['given_name'],
             'familyName': user['embeds']['users']['data']['attributes']['family_name']} for user in users
        ],
        'titles': [
            {'title': node['attributes']['title']}
        ],
        'publisher': 'Open Science Framework',
        'publicationYear': str(datetime.datetime.now().year),
        'resourceType': {
            'resourceType': 'Registration',
            'resourceTypeGeneral': 'Text'
        }
    }

    if node['attributes']['description']:
        data['descriptions'] = [{
            'descriptionType': 'Abstract',
            'description': node['attributes']['description']
        }]

    if node['attributes']['node_license']:
        data['rightsList'] = [{
            'rights': node['embeds']['license']['data']['attributes']['name'],
            'rightsURI': node['embeds']['license']['data']['attributes']['url']
        }]

    # Validate dictionary
    assert schema40.validate(data)

    # Generate DataCite XML from dictionary.
    return schema40.tostring(data)


def fetch_node(guid):
    return requests.get(f'{BASE_URL}v2/registrations/{guid}/?embed=provider&embed=contributors&embed=license').json()['data']


def main(guid, destination):
    json_data = fetch_node(guid)
    xml_metadata = build_metadata(json_data)
    with open(os.path.join(destination, 'datacite.xml'), 'w') as fp:
        fp.write(xml_metadata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-id', '--guid', help='The guid of the registration that you want to get datacite metadata for.')
    parser.add_argument('-d', '--destination', help='The parent directory a the file is copied into.')
    args = parser.parse_args()
    guid = args.guid
    destination = args.destination
    main(guid, destination)
