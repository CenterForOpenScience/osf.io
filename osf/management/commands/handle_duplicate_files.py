import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from osf.models import AbstractNode, Guid
from addons.osfstorage.models import BaseFileNode
from django.db import transaction

logger = logging.getLogger(__name__)

FOLDER = 'osf.osfstoragefolder'


# For a specific file type, returns items that have duplicate
# target_object_ids, names, parent_id, type, and _path
# Basically, any items in same location with the same name.
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
    FOLDER
]

def compare_location_and_region(first_file, second_file):
    """
    Compares versions for osfstoragefiles -
    Compares location['bucket'] and location['object'].
    Also compares version region_ids.
    """
    first_loc = first_file['versions__location']
    second_loc = second_file['versions__location']

    if first_loc and second_loc:
        return first_loc['bucket'] == second_loc['bucket'] and \
            first_loc['object'] == second_loc['object'] and \
            first_file['versions__region_id'] == first_file['versions__region_id']
    return False

def build_filename_set(files):
    """
    Convenience method for building a set of filenames
    """
    return set(files.values_list('name', flat=True).order_by('name'))

def recursively_compare_folders(resource_one, resource_two):
    """
    Recursively compares the contents of two folders - assumes initial resource_one
    and resource_two have the same name
    """
    match = True
    item_count = 0
    files_list_one = BaseFileNode.objects.filter(parent_id=resource_one['id'])
    files_list_two = BaseFileNode.objects.filter(parent_id=resource_two['id'])
    if len(files_list_one) != len(files_list_two) or \
            build_filename_set(files_list_one) != build_filename_set(files_list_two):
        match = False

    files_list_one = return_basefilenode_values(files_list_one)
    while match and (item_count < len(files_list_one)):
        resource_one = files_list_one[item_count]
        resource_two = return_basefilenode_values(files_list_two.filter(name=resource_one['name'])).first()
        match = resources_match(resource_one, resource_two) if resource_two else False
        item_count += 1
    return match

def resources_match(resource_one, resource_two):
    """
    Checks if resource_one and resource_two match.  If two folders, recursively compares contents.
    If two files, compares versions.
    """
    if resource_one['type'] == FOLDER:
        match = recursively_compare_folders(resource_one, resource_two)
    else:
        match = compare_versions(resource_one, resource_two)
    return match

def compare_history(first_file, second_file):
    """
    Compares _history field on files.  Addons in these scenarios
    are very unlikely to have versions, so we must compare their _history.
    """
    first_hist = first_file['_history']
    second_hist = second_file['_history']

    if first_hist and second_hist:
        return first_hist == second_hist
    return False

def stage_removal(preserved_file, next_file):
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

def return_basefilenode_values(file_queryset):
    """
    Returns an IncludeQuerySet that has the minimum values that we need to do
    a file comparison
    """
    return file_queryset.values(
        '_id',
        'id',
        'type',
        'versions__location',
        'versions__region_id',
        'guids___id',
        '_history',
        'name',
    )

def compare_versions(first_file, second_file):
    """
    Compares version and _history information. If either one matches, assume the files are a match
    """
    versions_equal = compare_location_and_region(first_file, second_file)
    history_equal = compare_history(first_file, second_file)

    return versions_equal or history_equal

def inspect_duplicates(file_summary):
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

        files = return_basefilenode_values(
            BaseFileNode.objects.filter(
                name=name,
                type=file_type,
                target_object_id=target_id,
                parent_id=parent_id,
                _path=path
            ).order_by('created')
        )

        preserved_file = files.first()

        for next_file in files.exclude(_id=preserved_file['_id']):
            safe_to_remove = resources_match(preserved_file, next_file)
            if safe_to_remove:
                to_remove.append(stage_removal(preserved_file, next_file))

        if not safe_to_remove:
            error_counter += 1
            logger.info('Contact admins to resolve: target: {}, name: {}'.format(target._id, name))

    logger.info('{}/{} errors to manually resolve.'.format(error_counter, len(file_summary)))
    logger.info('Files that can be deleted without issue:')
    for entry in to_remove:
        logger.info('{}'.format(entry))
    return to_remove

def remove_duplicates(duplicate_array, file_type):
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


class Command(BaseCommand):
    help = """
    Searches for literal file or folder duplicates caused by dropped partial unique filename constraint

    For osfstoragefiles - same name, same path, same parent,
    same target, same type - versions all have identical SHA's

    other addons -  have the same _history

    Repoints guids, and then deletes all but one of the dupes.
    """

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
            required=True,
            help='File type - must be in valid_file_types or "all-files" or "all"',
        )

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        dry_run = options['dry_run']
        file_type = options['file_type']

        if file_type not in valid_file_types and file_type not in ['all', 'all-files']:
            raise Exception('This is not a valid filetype.')

        if file_type == 'all':
            file_types = valid_file_types
        elif file_type == 'all-files':
            file_types = [t for t in valid_file_types if t != FOLDER]
        else:
            file_types = [file_type]

        if dry_run:
            logger.info('Dry Run. Data will not be modified.')

        for file_type in file_types:
            type_start_time = datetime.datetime.now()
            with connection.cursor() as cursor:
                logger.info('Examining duplicates for {}'.format(file_type))
                cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [file_type])
                duplicate_files = cursor.fetchall()

            to_remove = inspect_duplicates(duplicate_files)
            if not dry_run:
                with transaction.atomic():
                    remove_duplicates(to_remove, file_type)
            type_finish_time = datetime.datetime.now()
            logger.info('{} run time {}'.format(file_type, type_finish_time - type_start_time))

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
