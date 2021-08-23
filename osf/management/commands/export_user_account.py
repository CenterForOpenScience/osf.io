# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime as dt
import time
import io
import os
import json
import logging
import requests
import shutil
import tempfile

from django.db.models import Q
from django.core import serializers
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFile
from addons.wiki.models import WikiPage
from framework.auth.core import Auth
from osf.models import (
    AbstractNode,
    FileVersion,
    OSFUser,
    Preprint,
    Registration,
    QuickFilesNode
)
from osf.utils.workflows import DefaultStates
from scripts.utils import Progress
from api.base.utils import waterbutler_api_url_for
from api.base.settings.defaults import GBs

ERRORS = []
TMP_PATH = tempfile.mkdtemp()

PREPRINT_EXPORT_FIELDS = [
    'title',
    'description',
    'is_published',
    'created',
    'modified',
    'date_published'
]

NODE_EXPORT_FIELDS = [
    'title',
    'is_fork',
    'category',
    'is_public',
    'description',
    'forked_date',
    'created',
    'modified'
]

REGISTRATION_EXPORT_FIELDS = NODE_EXPORT_FIELDS + [
    'registered_data',
    'registered_meta'
]

logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def export_metadata(node, current_dir):
    """
    Exports the pretty printed serialization of a given model instance to metadata.json.
    Only simple fields (non-FK, non-M2M, etc) are serialized.

    """
    export_fields = NODE_EXPORT_FIELDS
    if isinstance(node, Registration):
        export_fields = REGISTRATION_EXPORT_FIELDS
    elif isinstance(node, Preprint):
        export_fields = PREPRINT_EXPORT_FIELDS
    with open(os.path.join(current_dir, 'metadata.json'), 'w') as f:
        # only write the fields dict, throw away pk and model_name
        metadata = json.loads(serializers.serialize('json', [node], fields=export_fields))
        json.dump(metadata[0]['fields'], f, indent=4, sort_keys=True)

def export_files(node, user, current_dir):
    """
    Creates a "files" directory within the current directory.
    Exports all of the OSFStorage files for a given node.
    Uses WB's download zip functionality to download osfstorage-archive.zip in a single request.

    """
    files_dir = os.path.join(current_dir, 'files')
    os.mkdir(files_dir)
    response = requests.get(
        url=waterbutler_api_url_for(
            node_id=node._id,
            _internal=True,
            provider='osfstorage',
            zip='',
            cookie=user.get_or_create_cookie(),
            base_url=node.osfstorage_region.waterbutler_url
        )
    )
    if response.status_code == 200:
        with open(os.path.join(files_dir, 'osfstorage-archive.zip'), 'wb') as f:
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
    wikis_dir = os.path.join(current_dir, 'wikis')
    os.mkdir(wikis_dir)
    for wiki in WikiPage.objects.get_wiki_pages_latest(node):
        if wiki.content:
            with io.open(os.path.join(wikis_dir, '{}.md'.format(wiki.wiki_page.page_name)), 'w', encoding='utf-8') as f:
                f.write(wiki.content)

def export_resource(node, user, current_dir):
    """
    Exports metadata, files, and wikis for given node (project, registration, or preprint).
    If the given node has children,
        Creates a "components" directory.
        Recursively exports the node's children.
        Note: *Sometimes* an empty "components" directory will be created if the given node has children,
        but the user being exported does not have access to them.

    """
    export_metadata(node, current_dir)
    if hasattr(node, 'wikis') and WikiPage.objects.get_wiki_pages_latest(node):
        export_wikis(node, current_dir)
    ctype = ContentType.objects.get_for_model(node.__class__)
    if OsfStorageFileNode.objects.filter(target_object_id=node.id, target_content_type=ctype):
        export_files(node, user, current_dir)

    if hasattr(node, 'find_readable_descendants'):
        descendants = list(node.find_readable_descendants(Auth(user)))
        if len(descendants):
            components_dir = os.path.join(current_dir, 'components')
            os.mkdir(components_dir)
            for child in descendants:
                current_dir = os.path.join(components_dir, child._id)
                os.mkdir(current_dir)
                export_resource(child, user, current_dir)

def export_resources(nodes_to_export, user, dir, nodes_type):
    """
    Creates appropriate directory structure and exports a given set of resources
    (projects, registrations, quickfiles or preprints) by calling export helper functions.

    """
    progress = Progress()
    progress.start(nodes_to_export.count(), nodes_type.upper())
    for node in nodes_to_export:
        current_dir = os.path.join(dir, node._id)
        os.mkdir(current_dir)
        export_resource(node, user, current_dir)
        progress.increment()
    progress.stop()

def get_usage(user):
    # includes nodes, registrations, quickfiles
    nodes = user.nodes.filter(is_deleted=False).exclude(type='osf.collection').values_list('id', flat=True)
    node_ctype = ContentType.objects.get_for_model(AbstractNode)
    node_files = get_resource_files(nodes, node_ctype)

    preprint_ctype = ContentType.objects.get_for_model(Preprint)
    preprint_files = get_resource_files(get_preprints_to_export(user), preprint_ctype)

    versions = FileVersion.objects.filter(Q(basefilenode__in=node_files) | Q(basefilenode__in=preprint_files))
    return sum([v.size or 0 for v in versions]) / GBs

def get_resource_files(resource_list, resource_ctype):
    return OsfStorageFile.objects.filter(target_object_id__in=resource_list, target_content_type=resource_ctype).values_list('id', flat=True)

def get_preprints_to_export(user):
    return Preprint.objects.filter(
        Q(preprintcontributor__user_id=user.id) &
        Q(deleted__isnull=True) &
        ~Q(machine_state=DefaultStates.INITIAL.value)
    )


def export_account(user_id, path, only_private=False, only_admin=False, export_files=True, export_wikis=True):
    """
    Exports (as a zip file) all of the projects, registrations, and preprints for which the given user is a contributor.

    The directory structure of the exported file is:

    <user_fullname> (<user_guid>).zip
        preprints/
            <preprint_guid>/
                metadata.json
                files/
                    osfstorage-archive.zip
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

        quickfiles/
            <quickfiles_id>/
                metadata.json
                files/
                    osfstorage-archive.zip

    """
    user = OSFUser.objects.get(guids___id=user_id, guids___id__isnull=False)
    proceed = input('\nUser has {:.2f} GB of data in OSFStorage that will be exported.\nWould you like to continue? [y/n] '.format(get_usage(user)))
    if not proceed or proceed.lower() != 'y':
        print('Exiting...')
        exit(1)

    base_dir = os.path.join(TMP_PATH, user_id)
    preprints_dir = os.path.join(base_dir, 'preprints')
    projects_dir = os.path.join(base_dir, 'projects')
    registrations_dir = os.path.join(base_dir, 'registrations')
    quickfiles_dir = os.path.join(base_dir, 'quickfiles')

    os.mkdir(base_dir)
    os.mkdir(preprints_dir)
    os.mkdir(projects_dir)
    os.mkdir(registrations_dir)
    os.mkdir(quickfiles_dir)

    preprints_to_export = get_preprints_to_export(user)

    projects_to_export = (user.nodes
        .filter(is_deleted=False, type='osf.node')
        .get_roots()
    )

    registrations_to_export = (user.nodes
        .filter(is_deleted=False, type='osf.registration', retraction__isnull=True)
        .get_roots()
    )

    quickfiles_to_export = (
        QuickFilesNode.objects.filter(creator=user)
    )

    export_resources(projects_to_export, user, projects_dir, 'projects')
    export_resources(preprints_to_export, user, preprints_dir, 'preprints')
    export_resources(registrations_to_export, user, registrations_dir, 'registrations')
    export_resources(quickfiles_to_export, user, quickfiles_dir, 'quickfiles')

    timestamp = dt.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
    output = os.path.join(path, '{user_id}-export-{timestamp}'.format(**locals()))
    print('Creating {output}.zip ...').format(**locals())
    shutil.make_archive(output, 'zip', base_dir)
    shutil.rmtree(base_dir)

    finished_msg = 'Finished without errors.' if not ERRORS else 'Finished with errors logged below.'
    print(finished_msg)

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
            'user',
            type=str,
            help='GUID of the user account to export.'
        )
        parser.add_argument(
            '--path',
            type=str,
            required=True,
            help='Path where to save the output file.'
        )

    def handle(self, *args, **options):
        export_account(
            user_id=options['user'],
            path=options['path'],
        )
