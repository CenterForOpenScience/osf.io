import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from osf.models import AbstractNode
from addons.osfstorage.models import BaseFileNode

logger = logging.getLogger(__name__)

# # TODO:
"""
1) Figure out how to tell if Files with no versions are literal duplicates
2) If literal duplicate, repoint guids and mark all files except the first as trashed Files
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
    'osf.owncloudfile'
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

    def get_version_info(self, file):
        # Returns a tuple with a dictionary of location info and the region id
        return file.versions.values_list('location', 'region_id', 'metadata')

    def get_version_metadata(self, versions_tuple):
        metadata = versions_tuple[0][2]
        commitSha = metadata['extra'].get('commitSha')
        if commitSha:
            return {'commitSha': commitSha}
        return None

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

    def examine_duplicates(self, duplicate_files, file_type):
        num_files = len(duplicate_files)
        num_errored = 0
        repoint_guids = 0
        for record in duplicate_files:
            target_id = record[0]
            name = record[1]
            parent_id = record[2]
            path = record[4]
            error = ''

            node = AbstractNode.objects.get(id=target_id)
            files = BaseFileNode.objects.filter(name=name, type=file_type, target_object_id=target_id, parent_id=parent_id, _path=path).order_by('created')
            first_file_versions = self.get_version_info(files[0])

            # For each duplicate file, compare its version information to see if it's an exact match.
            for file in files[1:]:
                next_file_versions = self.get_version_info(file)
                if not first_file_versions or not next_file_versions:
                    error = 'No versions found.'
                    continue
                if not first_file_versions[0][0] or not next_file_versions[0][0]:
                    # if self.get_version_metadata(first_file_versions) != self.get_version_metadata(next_file_versions):
                    error = 'No location information.'
                    continue
                if (self.get_version_locations(next_file_versions) != self.get_version_locations(first_file_versions) or
                        self.get_version_region(next_file_versions) != self.get_version_region(first_file_versions)):
                    error = 'Version discrepancies.'
                    continue

            repoint = files.last().get_guid()
            if repoint:
                repoint_guids += 1
            if error:
                num_errored += 1
                self.log_error(error, node, name, files)

        logger.info('{}/{} errors must be addressed manually for type {}'.format(num_errored, num_files, file_type))
        logger.info('{}/{} have guids that will have to be repointed.'.format(repoint_guids, num_files))

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
            if not dry_run:
                logger.info('Examining duplicates for {}'.format(file_type))
                cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [file_type])
                duplicate_files = cursor.fetchall()
                self.examine_duplicates(duplicate_files, file_type)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
