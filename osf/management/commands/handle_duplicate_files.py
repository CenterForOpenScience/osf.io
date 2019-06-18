import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from osf.models import AbstractNode, Guid
from addons.osfstorage.models import BaseFileNode

logger = logging.getLogger(__name__)


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
valid_file_types = [
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
    help = """
    Searches for literal file duplicates caused by dropped partial unique filename constraint

    For osfstoragefiles - same name, same path, same parent,
    same target, same type - versions all have identical SHA's

    other addons -  have the same _history

    Repoints guids, and then deletes all but one of the dupes.
    """
    def compare_versions(self, first_file, second_file):
        """
        Compares location['bucket'] and location['object'] values on versions.
        Also compares version region_ids.
        """
        first_loc = first_file['versions__location']
        second_loc = second_file['versions__location']

        if first_loc and second_loc:
            return first_loc['bucket'] == second_loc['bucket'] and \
                first_loc['object'] == second_loc['object'] and \
                first_file['versions__region_id'] == first_file['versions__region_id']
        return False

    def compare_history(self, first_file, second_file):
        """
        Compares _history field on files.
        """
        first_hist = first_file['_history']
        second_hist = second_file['_history']

        if first_hist and second_hist:
            return first_hist == second_hist
        return False

    def stage_removal(self, preserved_file, next_file):
        """
        Returns dictionary of staged items to delete.
        If the next_file has a guid, it will be repointed to the preserved_file.
        The next_file will be deleted.
        """
        info = {
            'guid_to_repoint': next_file['guids___id'],
            'to_remove': next_file['_id'],
            'preserving': preserved_file['_id']
        }
        return info

    def inspect_duplicates(self, dry_run, file_summary):
        """
        Inspects duplicates of a particular filetype and determines how many need to be resolved manually.
        Outputs an array of files that can be successfully deleted.
        """
        to_remove = []
        error_counter = 0

        for duplicate_record in file_summary:
            safe_to_remove = True
            target_id, name, parent_id, file_type, path, count = duplicate_record
            target = AbstractNode.objects.get(id=target_id)

            files = BaseFileNode.objects.filter(
                name=name,
                type=file_type,
                target_object_id=target_id,
                parent_id=parent_id,
                _path=path
            ).order_by('created').values(
                '_id', 'versions__location', 'versions__region_id', 'guids___id', '_history',
            )

            preserved_file = files.first()

            for next_file in files.exclude(_id=preserved_file['_id']):
                versions_equal = self.compare_versions(preserved_file, next_file)
                history_equal = self.compare_history(preserved_file, next_file)

                if versions_equal or history_equal:
                    to_remove.append(self.stage_removal(preserved_file, next_file))
                else:
                    safe_to_remove = False

            if not safe_to_remove:
                error_counter += 1
                logger.info('Contact admins to resolve: target: {}, name: {}'.format(target._id, name))

        logger.info('{}/{} errors to manually resolve.'.format(error_counter, len(file_summary)))
        logger.info('Files that can be deleted without issue:')
        for entry in to_remove:
            logger.info('{}'.format(entry))
        return to_remove

    def remove_duplicates(self, duplicate_array, file_type):
        """
        :param duplicate_array, expecting an array of dictionaries of format
            [{'guid_to_repoint': guid, 'to_remove': file__id, 'preserving': file__id}]
        """
        for duplicate in duplicate_array:
            guid = Guid.load(duplicate['guid_to_repoint'])
            preserving = BaseFileNode.objects.get(_id=duplicate['preserving'])
            to_remove = BaseFileNode.objects.get(_id=duplicate['to_remove'])

            if guid:
                guid.referent = preserving
                guid.save()

            to_remove.delete()
        logger.info('Duplicates removed of type {}'.format(file_type))

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
            help='File type - must be in valid_file_types',
        )

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        dry_run = options['dry_run']
        file_type = options['file_type']

        if file_type not in valid_file_types:
            raise Exception('This is not a valid filetype.')

        if dry_run:
            logger.info('Dry Run. Data will not be modified.')

        with connection.cursor() as cursor:
            logger.info('Examining duplicates for {}'.format(file_type))
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [file_type])
            duplicate_files = cursor.fetchall()

        to_remove = self.inspect_duplicates(dry_run, duplicate_files)
        if not dry_run:
            self.remove_duplicates(to_remove, file_type)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
