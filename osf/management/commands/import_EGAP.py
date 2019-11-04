# -*- coding: utf-8 -*-
import logging

import os
import json
import shutil
import requests
import tempfile
from django.core.management.base import BaseCommand
from osf.utils.permissions import WRITE
from osf.models import (
    RegistrationSchema,
    Node,
    DraftRegistration,
    OSFUser
)
from website.project.metadata.schemas import ensure_schema_structure, from_json
from website.settings import WATERBUTLER_INTERNAL_URL
from osf_tests.factories import ApiOAuth2PersonalTokenFactory
from framework.auth.core import Auth
from zipfile import ZipFile

logger = logging.getLogger(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))


class EGAPUploadException(Exception):
    pass


def ensure_egap_schema():
    schema = ensure_schema_structure(from_json('egap-registration.json'))
    schema_obj, created = RegistrationSchema.objects.update_or_create(
        name=schema['name'],
        schema_version=schema.get('version', 1),
        defaults={
            'schema': schema,
        }
    )
    if created:
        schema_obj.save()
    return RegistrationSchema.objects.get(name='EGAP Registration')


def get_creator_auth_header(creator_username):
    creator = OSFUser.objects.get(username=creator_username)
    token = ApiOAuth2PersonalTokenFactory(owner=creator)
    token.save()
    return creator, {'Authorization': 'Bearer {}'.format(token.token_id)}


def create_node_from_project_json(egap_assets_path, epag_project_dir, creator):
    with open(os.path.join(egap_assets_path, epag_project_dir, 'project.json'), 'r') as fp:
        project_data = json.load(fp)
        title = project_data['title']
        node = Node(title=title, creator=creator)
        node.save()  # must save before adding contribs for auth reasons

        for contributor in project_data['contributors']:
            node.add_contributor_registered_or_not(
                Auth(creator),
                full_name=contributor['name'],
                email=contributor['email'],
                permissions=WRITE,
                send_email='false'
            )

        node.set_visible(creator, visible=False, log=False, save=True)

    return node


def recursive_upload(auth, node, dir_path, parent='', metadata=list()):
    try:
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            base_url = '{}/v1/resources/{}/providers/osfstorage/{}'.format(WATERBUTLER_INTERNAL_URL, node._id, parent)
            if os.path.isfile(item_path):
                with open(item_path, 'rb') as fp:
                    url = base_url + '?name={}&kind=file'.format(item)
                    resp = requests.put(url, data=fp.read(), headers=auth)
            else:
                url = base_url + '?name={}&kind=folder'.format(item)
                resp = requests.put(url, headers=auth)
                metadata = recursive_upload(auth, node, item_path, parent=resp.json()['data']['attributes']['path'], metadata=metadata)

            if resp.status_code == 409:  # if we retry something already uploaded just skip.
                continue

            if resp.status_code != 201:
                raise EGAPUploadException('Error waterbutler response is {}, with {}'.format(resp.status_code, resp.content))

            metadata.append(resp.json())
    except EGAPUploadException as e:
        logger.info(str(e))
        metadata = recursive_upload(auth, node, dir_path, parent=parent, metadata=metadata)

    return metadata


def get_egap_assets(guid, creator_auth):
    node = Node.load(guid)
    zip_file = node.files.first()
    temp_path = tempfile.mkdtemp()

    url = '{}/v1/resources/{}/providers/osfstorage/{}'.format(WATERBUTLER_INTERNAL_URL, guid, zip_file._id)
    zip_file = requests.get(url, headers=creator_auth).content

    egap_assets_path = os.path.join(temp_path, 'egap_assets.zip')

    with open(egap_assets_path, 'w') as fp:
        fp.write(zip_file)

    with ZipFile(egap_assets_path, 'r') as zipObj:
        zipObj.extractall(temp_path)

    return temp_path


def main(guid, creator_username):
    egap_schema = ensure_egap_schema()
    creator, creator_auth = get_creator_auth_header(creator_username)

    egap_assets_path = get_egap_assets(guid, creator_auth)

    # __MACOSX is a hidden file created by the os when zipping
    directory_list = [directory for directory in os.listdir(egap_assets_path) if directory not in ('egap_assets.zip', '__MACOSX')]

    for epag_project_dir in directory_list:
        node = create_node_from_project_json(egap_assets_path, epag_project_dir, creator=creator)

        non_anon_files = os.path.join(egap_assets_path, epag_project_dir, 'data', 'nonanonymous')
        non_anon_metadata = recursive_upload(creator_auth, node, non_anon_files)

        anon_files = os.path.join(egap_assets_path, epag_project_dir, 'data', 'anonymous')
        if os.path.isdir(anon_files):
            anon_metadata = recursive_upload(creator_auth, node, anon_files)
        else:
            anon_metadata = {}

        with open(os.path.join(egap_assets_path, epag_project_dir, 'registration-schema.json'), 'r') as fp:
            registration_metadata = json.load(fp)

        # add selectedFileName Just so filenames are listed in the UI
        for data in non_anon_metadata:
            data['selectedFileName'] = data['data']['attributes']['name']

        for data in anon_metadata:
            data['selectedFileName'] = data['data']['attributes']['name']

        non_anon_titles = ', '.join([data['data']['attributes']['name'] for data in non_anon_metadata])
        registration_metadata['q37'] = {'comments': [], 'extra': non_anon_metadata, 'value': non_anon_titles}

        anon_titles = ', '.join([data['data']['attributes']['name'] for data in anon_metadata])
        registration_metadata['q38'] = {'comments': [], 'extra': anon_metadata, 'value': anon_titles}

        DraftRegistration.create_from_node(
            node,
            user=creator,
            schema=egap_schema,
            data=registration_metadata,
        )

    shutil.rmtree(egap_assets_path)


class Command(BaseCommand):
    """Magically morphs csv data into lovable nodes with draft registrations attached
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-c',
            '--creator',
            help='This should be the username of the initial adminstrator for the imported nodes',
            required=True
        )
        parser.add_argument(
            '-id',
            '--guid',
            help='This should be the guid of the private project with the directory structure',
            required=True
        )

    def handle(self, *args, **options):
        creator_username = options.get('creator', False)
        guid = options.get('guid', False)
        main(guid, creator_username)
