# -*- coding: utf-8 -*-
from datetime import datetime as dt
import pytz
import logging

import re
import os
import json
import shutil
import requests
import tempfile
from django.core.management.base import BaseCommand

from osf.utils.permissions import ADMIN, WRITE
from osf.models import (
    ApiOAuth2PersonalToken,
    RegistrationSchema,
    Node,
    DraftRegistration,
    OSFUser
)
from osf.models.nodelog import NodeLog
from website.project.metadata.schemas import ensure_schema_structure, from_json
from website.settings import WATERBUTLER_INTERNAL_URL
from framework.auth.core import Auth
from zipfile import ZipFile

logger = logging.getLogger(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

check_id = lambda item: re.match(r'(^[0-9]{8}[A-Z]{2})', item)


class EGAPUploadException(Exception):
    pass


def ensure_egap_schema():
    schema = ensure_schema_structure(from_json('egap-registration-3.json'))
    schema_obj, created = RegistrationSchema.objects.update_or_create(
        name=schema['name'],
        schema_version=schema.get('version', 1),
        defaults={
            'schema': schema,
        }
    )
    if created:
        schema_obj.save()
    return RegistrationSchema.objects.get(name='EGAP Registration', schema_version=3)


def get_creator_auth_header(creator_username):
    creator = OSFUser.objects.get(username=creator_username)

    token, created = ApiOAuth2PersonalToken.objects.get_or_create(name='egap_creator', owner=creator)
    if created:
        token.save()

    return creator, {'Authorization': 'Bearer {}'.format(token.token_id)}


def create_node_from_project_json(egap_assets_path, egap_project_dir, creator):
    with open(os.path.join(egap_assets_path, egap_project_dir, 'project.json'), 'r') as fp:
        project_data = json.load(fp)
        title = project_data['title']
        node = Node(title=title, creator=creator)
        node.save()  # must save before adding contribs for auth reasons

        for contributor in project_data['contributors']:
            email = ''
            if contributor.get('email'):
                email = contributor.get('email').strip()
                email = email.split('\\u00a0')[0].split(',')[0]
                if '<' in email:
                    email = email.split('<')[1].replace('>', '')

            node.add_contributor_registered_or_not(
                Auth(creator),
                full_name=contributor['name'],
                email=email,
                permissions=WRITE,
                send_email='false'
            )

        node.set_visible(creator, visible=False, log=False, save=True)

    return node


def rollback_node_from_project_json(egap_assets_path, egap_project_dir, creator):
    with open(os.path.join(egap_assets_path, egap_project_dir, 'project.json'), 'r') as fp:
        project_data = json.load(fp)
        title = project_data['title']
        try:
            node = Node.objects.filter(title=title, creator=creator).get()
        except Exception:
            logger.error(
                'Attempted rollback on Node titled {}. Node was not created.'.format(title)
            )
            return
        node.delete()

    return


def recursive_upload(auth, node, dir_path, parent='', metadata=None):

    if metadata is None:
        metadata = []

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

    with open(egap_assets_path, 'wb') as fp:
        fp.write(zip_file)

    with ZipFile(egap_assets_path, 'r') as zipObj:
        zipObj.extractall(temp_path)
        zip_parent = [file for file in os.listdir(temp_path) if file not in ('__MACOSX', 'egap_assets.zip') and not check_id(file)]
        if zip_parent:
            zip_parent = zip_parent[0]
            for i in os.listdir(os.path.join(temp_path, zip_parent)):
                shutil.move(os.path.join(temp_path, zip_parent, i), os.path.join(temp_path, i))

    if zip_parent:
        os.rmdir(os.path.join(temp_path, zip_parent))

    return temp_path

def register_silently(draft_registration, auth, sanction_type, external_registered_date, embargo_end_date):
    registration = draft_registration.register(auth, save=True)
    registration.external_registration = True
    registration.registered_date = external_registered_date

    registration.registered_from.add_log(
        action=NodeLog.EXTERNAL_REGISTRATION_CREATED,
        params={
            'node': registration.registered_from._id,
            'registration': registration._id
        },
        auth=auth,
        log_date=external_registered_date)
    registration.registered_from.add_log(
        action=NodeLog.EXTERNAL_REGISTRATION_IMPORTED,
        params={
            'node': registration.registered_from._id,
            'registration': registration._id
        },
        auth=auth,
        log_date=dt.now().replace(tzinfo=pytz.utc))

    if sanction_type == 'Embargo':
        registration.embargo_registration(auth.user, embargo_end_date)
    else:
        registration.require_approval(auth.user)

    registration.save()

def main(guid, creator_username):
    egap_schema = ensure_egap_schema()
    creator, creator_auth = get_creator_auth_header(creator_username)

    egap_assets_path = get_egap_assets(guid, creator_auth)

    # __MACOSX is a hidden file created by the os when zipping
    directory_list = [directory for directory in os.listdir(egap_assets_path) if directory not in ('egap_assets.zip', '__MACOSX') and not directory.startswith('.')]

    directory_list.sort()
    for egap_project_dir in directory_list:
        logger.info(
            'Attempting to import the follow directory: {}'.format(egap_project_dir)
        )
        # Node Creation
        try:
            node = create_node_from_project_json(egap_assets_path, egap_project_dir, creator=creator)
        except Exception as err:
            logger.error(
                'There was an error attempting to create a node from the '
                '{} directory. Attempting to rollback node and contributor creation'.format(egap_project_dir)
            )
            logger.error(str(err))
            try:
                rollback_node_from_project_json(egap_assets_path, egap_project_dir, creator=creator)
            except Exception as err:
                logger.error(str(err))
            continue

        # Node File Upload
        non_anon_files = os.path.join(egap_assets_path, egap_project_dir, 'data', 'nonanonymous')
        non_anon_metadata = recursive_upload(creator_auth, node, non_anon_files)

        anon_files = os.path.join(egap_assets_path, egap_project_dir, 'data', 'anonymous')
        if os.path.isdir(anon_files):
            anon_metadata = recursive_upload(creator_auth, node, anon_files)
        else:
            anon_metadata = {}

        # DraftRegistration Metadata Handling
        with open(os.path.join(egap_assets_path, egap_project_dir, 'registration-schema.json'), 'r') as fp:
            registration_metadata = json.load(fp)

        # add selectedFileName Just so filenames are listed in the UIj
        non_anon_metadata_dict = []
        for data in non_anon_metadata:
            if data['data']['attributes']['kind'] == 'folder':
                continue
            data['selectedFileName'] = data['data']['attributes']['name']
            data['sha256'] = data['data']['attributes']['extra']['hashes']['sha256']
            data['nodeId'] = node._id
            non_anon_metadata_dict.append(data)

        anon_metadata_dict = []
        for data in anon_metadata:
            if data['data']['attributes']['kind'] == 'folder':
                continue
            data['selectedFileName'] = data['data']['attributes']['name']
            data['sha256'] = data['data']['attributes']['extra']['hashes']['sha256']
            data['nodeId'] = node._id
            anon_metadata_dict.append(data)

        non_anon_titles = ', '.join([data['data']['attributes']['name'] for data in non_anon_metadata_dict])
        registration_metadata['q37'] = {'comments': [], 'extra': non_anon_metadata_dict, 'value': non_anon_titles}

        anon_titles = ', '.join([data['data']['attributes']['name'] for data in anon_metadata_dict])
        registration_metadata['q38'] = {'comments': [], 'extra': anon_metadata_dict, 'value': anon_titles}

        embargo_date = registration_metadata.pop('q12', None)

        # DraftRegistration Creation
        draft_registration = DraftRegistration.create_from_node(
            node=node,
            user=creator,
            schema=egap_schema,
            data=registration_metadata,
        )

        # Registration Creation
        logger.info(
            'Attempting to create a Registration for Project {}'.format(node._id)
        )

        # Retrieve EGAP registration date and potential embargo go-public date
        if registration_metadata.get('q4'):
            egap_registration_date_string = registration_metadata['q4']['value']
            egap_registration_date = dt.strptime(egap_registration_date_string, '%m/%d/%Y - %H:%M').replace(tzinfo=pytz.UTC)
        else:
            logger.error(
                'DraftRegistration associated with Project {} '
                'does not have a valid registration date in registration_metadata'.format(node._id)
            )
            continue

        if embargo_date:
            if embargo_date.get('value'):
                egap_embargo_public_date_string = embargo_date['value']
                egap_embargo_public_date = dt.strptime(egap_embargo_public_date_string, '%m/%d/%y').replace(tzinfo=pytz.UTC)
            else:
                egap_embargo_public_date = None
        else:
            egap_embargo_public_date = None

        sanction_type = 'RegistrationApproval'
        if egap_embargo_public_date and (egap_embargo_public_date > dt.today().replace(tzinfo=pytz.UTC)):
            sanction_type = 'Embargo'

        logger.info(
            'Attempting to register {} silently'.format(node._id)
        )
        try:
            register_silently(draft_registration, Auth(creator), sanction_type, egap_registration_date, egap_embargo_public_date)
        except Exception as err:
            logger.error(
                'Unexpected error raised when attempting to silently register '
                'project {}. Continuing...'.format(node._id))
            logger.info(str(err))
            continue

        # Update contributors on project to Admin
        contributors = node.contributor_set.all()
        for contributor in contributors:
            if contributor.user == creator:
                pass
            else:
                node.update_contributor(contributor.user, permission=ADMIN, visible=True, auth=Auth(creator), save=True)

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
