import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from osf.models import AbstractNode
from addons.osfstorage.models import BaseFileNode

logger = logging.getLogger(__name__)

"""
3) Get folder checks working
"""

FETCH_DUPLICATES_BY_FILETYPE = """
    SELECT *
    FROM (
      SELECT
        target_object_id,
        name,
        parent_id,
        type,
        _path,
        count(*) AS ct
      FROM osf_basefilenode
      WHERE type = %s
      AND name != ''
      GROUP BY (target_object_id, name, parent_id, type, _path)
    ) as foo
    WHERE ct > 1;
    """

# googledrive and trashedfile/folder/folders excluded.
file_types = [
    'osf.onedrivefile',
    'osf.gitlabfile',
    'osf.dropboxfile',
    'osf.githubfile',
    'osf.s3file',
    'osf.boxfile',
    'osf.figsharefile',
    'osf.osfstoragefile',
    'osf.bitbucketfile',
    'osf.owncloudfile',
    'osf.osfstoragefolder'
]

class Command(BaseCommand):
    help = '''
    Searches for literal file duplicates (same name, same path, same parent,
    same target, same type - versions all have identical SHA's)

    Repoints guids, and then deletes all but one of the dupes.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not repoint guids or delete dupes',
        )
        parser.add_argument(
            '--file_type',
            type=str,
            default='osf.osfstoragefile',
            help='File type - must be in file_types',
        )

    def get_version_info(self, file, file_type):
        if file_type == 'osf.osfstoragefile':
            # Returns a tuple of location and region_id information
            return file.versions.values_list('location', 'region_id')
        # Returns an array of dictionaries
        return file._history

    def get_version_locations(self, versions_tuple):
        # Pulls the version location's bucket and object (sha)
        location_dict = versions_tuple[0][0]
        return {'bucket': location_dict['bucket'], 'object': location_dict['object']}

    def get_version_region(self, versions_tuple):
        # Pulls the version's region id
        return versions_tuple[0][1]

    def log_error(self, error_message, node, name, files):
        logger.warning('error: {} node_id: {}, public: {}, # dupes: {}, filename: {}, '.format(
            error_message,
            node._id,
            node.is_public,
            files.count(),
            name.encode('utf-8'),
        ))

    def inspect_file_versions_for_errors(self, first_file_versions, next_file_versions, file_type):
        if not first_file_versions or not next_file_versions:
            return 'No versions found.'

        if file_type == 'osf.osfstoragefile':
            if not first_file_versions[0][0] or not next_file_versions[0][0]:
                return 'No location information.'
            if (self.get_version_locations(next_file_versions) != self.get_version_locations(first_file_versions) or
                    self.get_version_region(next_file_versions) != self.get_version_region(first_file_versions)):
                return 'Version discrepancies.'
        else:
            if first_file_versions != next_file_versions:
                return 'Addon discrepancies detected.'
        return None

    def inspect_children(self, target, first_file, second_file):
        if not first_file or not second_file:
            logger.error('Entry does not match, resolve manually: target: {}, name: {}'.format(target._id, first_file.name))
            return
        if first_file.kind == 'folder':
            if (not first_file or not second_file) or (first_file.name != second_file.name and first_file.kind != second_file.kind and first_file.target != second_file.target):
                logger.error('Folder does not match, resolve manually: target: {}, name: {}, type: {}'.format(target._id, first_file.name, 'osf.osfstoragefolder'))
            for child in first_file.children:
                matching_child = BaseFileNode.objects.filter(target_object_id=target.id, name=child.name, parent=second_file.parent).first()
                self.inspect_children(target, child, matching_child)
        else:
            file_type = 'osf.osfstoragefile'
            first_file_versions = self.get_version_info(first_file, 'osf.osfstoragefile')
            next_file_versions = self.get_version_info(second_file, file_type)
            error = self.inspect_file_versions_for_errors(first_file_versions, next_file_versions, file_type)
            print error

    def examine_duplicates(self, dry_run, duplicate_files, file_type):
        num_files = len(duplicate_files)
        num_errored = 0
        deleted_files = []
        repointed_guids = []

        for record in duplicate_files:
            target_id = record[0]
            name = record[1]

            node = AbstractNode.objects.get(id=target_id)
            files = BaseFileNode.objects.filter(
                name=name,
                type=file_type,
                target_object_id=target_id,
                parent_id=record[2],
                _path=record[4]
            ).order_by('created')

            first_file = files[0]
            second_file = files[1]

            if file_type == 'osf.osfstoragefolder':
                self.inspect_children(node, first_file, second_file)

            else:
                first_file_versions = self.get_version_info(first_file, file_type)
                logger.info('Preserving {} file {}, node {}, name {}'.format(file_type, first_file._id, node._id, name.encode('utf-8')))

                # For each duplicate file, compare its version information to see if it's an exact match.
                # Osfstorage files are comparing versions, and addons are comparing file _history
                for next_file in files[1:]:
                    next_file_versions = self.get_version_info(next_file, file_type)
                    error = self.inspect_file_versions_for_errors(first_file_versions, next_file_versions, file_type)
                    if not error and not dry_run:
                        deleted_file_id, guid_dict = self.remove_duplicates(first_file, next_file)
                        deleted_files.append(deleted_file_id)
                        repointed_guids.append(guid_dict)

                if error:
                    num_errored += 1
                    self.log_error(error, node, name, files)

        logger.info('{}/{} errors must be addressed manually for type {}'.format(num_errored, num_files, file_type))
        if not dry_run:
            logger.info('Deleted the following {} files {}.'.format(file_type, deleted_files))
            logger.info('Repointed the following {} guids {}.'.format(file_type, repointed_guids))

    def remove_duplicates(self, first_file, next_file):
        guid = next_file.get_guid()
        guid_dict = {}
        if guid:
            guid.referent = first_file
            guid.save()
            guid_dict = {
                'guid': guid._id,
                'former_referent': next_file._id,
                'current_referent': first_file._id}
        next_file.delete()
        return next_file._id, guid_dict

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)
        dry_run = options['dry_run']
        file_type = options['file_type']
        logger.debug(
            'Dry run: {}, file_type: {}'.format(
                dry_run,
                file_type,
            )
        )

        if file_type not in file_types:
            logger.warning('This is not a valid filetype.')
            raise
        if dry_run:
            logger.info('DRY RUN')
        with connection.cursor() as cursor:
            logger.info('Examining duplicates for {}'.format(file_type))
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [file_type])
            duplicate_files = cursor.fetchall()
            self.examine_duplicates(dry_run, duplicate_files, file_type)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
