# -*- coding: utf-8 -*-
import logging

import os
import json
import requests
import argparse
from django.core.management.base import BaseCommand
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

logger = logging.getLogger(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))


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
            node.add_contributor_registered_or_not(Auth(creator), full_name=contributor['name'], email=contributor['email'])

        node.set_visible(creator, visible=False, log=False, save=True)

    return node


def recursive_upload(auth, node, dir_path, parent='', metadata=list()):
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        base_url = '{}/v1/resources/{}/providers/osfstorage/{}'.format(WATERBUTLER_INTERNAL_URL, node._id, parent)

        if os.path.isfile(item_path):
            with open(item_path, 'rb') as fp:
                url = base_url + '?name={}&kind=file'.format(item)
                resp = requests.put(url, data=fp.read(), headers=auth)

            if resp.status_code != 201:
                raise Exception('Error waterbutler response is {}, with {}'.format(resp.status_code, resp.content))

            metadata.append(resp.json())
        else:
            url = base_url + '?name={}&kind=folder'.format(item)
            resp = requests.put(url, headers=auth)

            if resp.status_code != 201:
                raise Exception('Error waterbutler response is {}, with {}'.format(resp.status_code, resp.content))

            metadata.append(resp.json())

            metadata = recursive_upload(auth, node, item_path, parent=resp.json()['data']['attributes']['path'], metadata=metadata)

    return metadata


def main(creator_username):
    ensure_egap_schema()
    creator, creator_auth = get_creator_auth_header(creator_username)

    egap_assets_path = os.path.join(HERE, 'EGAP')
    egap_schema = RegistrationSchema.objects.get(name='EGAP Registration')

    for epag_project_dir in os.listdir(egap_assets_path):
        node = create_node_from_project_json(egap_assets_path, epag_project_dir, creator=creator)

        non_anon_files = os.path.join(egap_assets_path, epag_project_dir, 'data', 'nonanonymous')
        non_anon_metadata = recursive_upload(creator_auth, node, non_anon_files)

        anon_files = os.path.join(egap_assets_path, epag_project_dir, 'data', 'anonymous')
        if os.path.isdir(anon_files):
            anon_metadata = recursive_upload(creator_auth, node, anon_files)

        with open(os.path.join(egap_assets_path, epag_project_dir, 'registration-schema.json'), 'r') as fp:
            registration_metadata = json.load(fp)

        # add selectedFileName Just so filenames are listed in the UI
        for data in non_anon_metadata:
            data['selectedFileName'] = data['name']

        for data in anon_metadata:
            data['selectedFileName'] = data['name']

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

class Command(BaseCommand):
    """Magically morphs csv data into lovable nodes with draft registrations attached
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-c',
            '--creator',
            help='This should be the username of the initial adminstrator for the imported nodes'
        )

    def handle(self, *args, **options):
        creator_username = options.get('creator', False)
        main(creator_username)
