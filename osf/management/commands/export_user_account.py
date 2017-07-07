# -*- coding: utf-8 -*-
import io
import os
import json
import logging
import requests
import shutil

from django.core import serializers
from django.core.management.base import BaseCommand

from addons.wiki.models import NodeWikiPage
from addons.osfstorage.models import OsfStorageFileNode
from framework.auth.core import Auth
from osf.models import (
    OSFUser,
    PreprintService,
    Registration,
)
from scripts.utils import Progress
from website.util import waterbutler_api_url_for

PREPRINT_EXPORT_FIELDS = [
    'is_published',
    'date_created',
    'date_modified',
    'date_published'
]

NODE_EXPORT_FIELDS = [
    'title',
    'is_fork',
    'category',
    'is_public',
    'description',
    'forked_date',
    'date_created',
    'date_modified'
]

REGISTRATION_EXPORT_FIELDS = NODE_EXPORT_FIELDS + [
    'registered_data',
    'registered_meta'
]

logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ERRORS = []

def export_metadata(node, current_dir):
    """
    Exports the pretty printed serialization of a given model instance to metadata.json.
    Only simple fields (non-FK, non-M2M, etc) are serialized.

    """
    export_fields = NODE_EXPORT_FIELDS
    if isinstance(node, Registration):
        export_fields = REGISTRATION_EXPORT_FIELDS
    elif isinstance(node, PreprintService):
        export_fields = PREPRINT_EXPORT_FIELDS
    with open('{}metadata.json'.format(current_dir), 'w') as f:
        # only write the fields dict, throw away pk and model_name
        metadata = serializers.serialize('json', [node], fields=export_fields)
        f.write(json.dumps(metadata, indent=4, sort_keys=True))

def export_files(node, user, current_dir):
    """
    Creates a "files" directory within the current directory.
    Exports all of the OSFStorage files for a given node.
    Uses WB's download zip functionality to download osfstorage-archive.zip in a single request.

    """
    files_dir = '{}files/'.format(current_dir)
    os.mkdir(files_dir)
    response = requests.get(
        url=waterbutler_api_url_for(
            node_id=node._id,
            _internal=True,
            provider='osfstorage',
            zip='',
            cookie=user.get_or_create_cookie()
        )
    )
    if response.status_code == 200:
        with open('{}osfstorage-archive.zip'.format(files_dir), 'wb') as f:
            f.write(response.content)
    else:
        ERRORS.append(
            'Error exporting files for node {}. Waterbutler responded with a {} status code. Response: {}'
            .format(node._id, response.status_code, response.json())
        )

def export_wikis(node, current_dir):
    """
    Creates a "wikis" directory within the current directory.
    Exports all of the wiki pages for a given node as individual markdown files.

    """
    wikis_dir = '{}wikis/'.format(current_dir)
    os.mkdir(wikis_dir)
    for wiki_name, wiki_id in node.wiki_pages_current.iteritems():
        wiki = NodeWikiPage.objects.get(guids___id=wiki_id)
        if wiki.content:
            with io.open('{}{}.md'.format(wikis_dir, wiki_name), 'w', encoding='utf-8') as f:
                f.write(wiki.content)

def export_node(node, user, current_dir):
    """
    Exports metadata, files, and wikis for given node (project, registration, or preprint).
    If the given node has children,
        Creates a "components" directory.
        Recursively exports the node's children.
        Note: *Sometimes* an empty "components" directory will be created if the given node has children,
        but the user being exported does not have access to them.

    """
    export_metadata(node, current_dir)
    if node.wiki_pages_current:
        export_wikis(node, current_dir)
    if OsfStorageFileNode.objects.filter(node=node):
        export_files(node, user, current_dir)

    if node.nodes:
        components_dir = '{}components/'.format(current_dir)
        os.mkdir(components_dir)
        for child in node.find_readable_descendants(Auth(user)):
            current_dir = '{}{}/'.format(components_dir, child._id)
            os.mkdir(current_dir)
            export_node(child, user, current_dir)

def export_nodes(nodes_to_export, user, dir, nodes_type):
    """
    Creates appropriate directory structure and exports a given set of nodes
    (projects, registrations, or preprints) by calling export helper functions.

    """
    progress = Progress()
    if nodes_type == 'preprints':
        progress.start(nodes_to_export.count(), nodes_type.upper())
        for node in nodes_to_export:
            # export the preprint (just metadata)
            current_dir = '{}{}/'.format(dir, node._id)
            os.mkdir(current_dir)
            export_metadata(node, current_dir)
            # export the associated project (metadata, files, wiki, etc)
            current_dir = '{}{}/'.format(dir, node.node._id)
            os.mkdir(current_dir)
            export_node(node.node, user, current_dir)
            progress.increment()
        progress.stop()
    else:
        progress.start(nodes_to_export.count(), nodes_type.upper())
        for node in nodes_to_export:
            current_dir = '{}{}/'.format(dir, node._id)
            os.mkdir(current_dir)
            export_node(node, user, current_dir)
            progress.increment()
        progress.stop()

def export_account(user_id, only_private=False, only_admin=False, export_files=True, export_wikis=True):
    """
    Exports (as a zip file) all of the projects, registrations, and preprints for which the given user is a contributor.

    The directory structure of the exported file is:

    <user_fullname> (<user_guid>).zip
        preprints/
            <preprint_guid>/
                metadata.json
                <project_guid>/
                    metadata.json
                    files/
                        osfstorage-archive.zip
                    wikis/
                        <wiki_page_name>.md

        projects/
            <project_guid>/
                metadata.json
                files/
                    osfstorage-archive.zip
                wikis/
                    <wiki_page_name>.md
                components/
                    <component_guid>/
                        metadata.json
                        files/
                        wikis/
                    <component_guid>/
                        metadata.json
                        files/
                        wikis/
                        components/
                            ...
        registrations/
            *same as projects*

    """
    user = OSFUser.objects.get(guids___id=user_id)

    base_dir = '{}/'.format(user_id)
    preprints_dir = '{}preprints/'.format(base_dir)
    projects_dir = '{}projects/'.format(base_dir)
    registrations_dir = '{}registrations/'.format(base_dir)

    os.mkdir(base_dir)
    os.mkdir(preprints_dir)
    os.mkdir(projects_dir)
    os.mkdir(registrations_dir)

    preprints_to_export = (PreprintService.objects
        .filter(node___contributors__guids___id=user_id)
        .select_related('node')
    )

    preprint_projects_exported = [preprint.node._id for preprint in preprints_to_export]
    projects_to_export = (user.nodes
        .filter(is_deleted=False, type='osf.node')
        .exclude(guids___id__in=preprint_projects_exported)
        .include('guids')
        .get_roots()
    )

    registrations_to_export = (user.nodes
        .filter(is_deleted=False, type='osf.registration', retraction__null=True, embargo__null=True)
        .include('guids')
        .get_roots()
    )

    export_nodes(projects_to_export, user, projects_dir, 'projects')
    export_nodes(preprints_to_export, user, preprints_dir, 'preprints')
    export_nodes(registrations_to_export, user, registrations_dir, 'registrations')

    print('Creating {} ({}).zip ...'.format(user.fullname, user_id))
    shutil.make_archive('{} ({})'.format(user.fullname, user_id), 'zip', user_id)

    print('Removing temp {}/ directory...'.format(user_id))
    shutil.rmtree(base_dir)

    for err in ERRORS:
        logger.error(err)


class Command(BaseCommand):

    def add_arguments(self, parser):
        # TODO: add arguments to narrow down what should be exported
        #   export only files and/or wikis
        #   export only projects/registrations/preprints
        #   export only private projects
        #   export only projects on which user is an admin
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='GUID of the user account to export.'
        )

    def handle(self, *args, **options):
        export_account(
            user_id=options['user'],
        )
