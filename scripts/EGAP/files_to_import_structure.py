import os
import re
import shutil
import argparse
from distutils.dir_util import copy_tree
import logging

from nose.tools import assert_equal

logger = logging.getLogger(__name__)


# This takes the item id from the path of the project directory for example '20121001AA Findley' -> '20121001AA'
get_item_id = lambda _path: _path.split(os.sep)[-1].split(' ')[0]


def get_project_id(root, source_dir):
    project_id_base = root.split(source_dir)[-1]
    if ' ' in project_id_base:
        project_id = project_id_base.split(' ')[0].split('/')[-1]
    else:
        project_id = project_id_base.split('/')[0]
    return project_id


# Check if file name starts with EGAP id for example '20121001AA_PAP.pdf'
def check_id(project_id, item):
    return item.startswith(project_id)


# Check if file follows anonymous naming convention
check_anon = lambda item: 'pap_anon' in item.lower() or 'anonymous' in item.lower()


def action_files_by_name(root, source_item, item_name):
    """
    Pick out anonymous and create new folder to move them into it, remove ones that don't follow id naming convention.
    :param root:
    :param source_item:
    :param item_name:
    :return:
    """
    project_id = get_project_id(root, source_item)
    path = os.path.join(root, item_name)
    if not check_id(project_id, item_name):
        os.remove(path)
        return

    if check_anon(item_name):
        destination_parent = os.path.join('/'.join(root.split('/')[:-1]), 'anonymous')

        if not os.path.exists(destination_parent):
            os.mkdir(destination_parent)
        destination_item = os.path.join(destination_parent, item_name)
        shutil.move(path, destination_item)


def audit_files(source_directory):
    logger.info('Running audit. Source: {}'.format(source_directory))

    including = open('including.txt', 'w+')
    ignoring = open('ignoring.txt', 'w+')
    for root, directory, files in os.walk(source_directory):
        for item in files:
            project_id = get_project_id(root, source_directory)
            name = '{}/{}'.format(root.split(source_directory)[-1], item)  # get file/folder name from just under source
            if not check_id(project_id, item):
                ignoring.writelines(name + '\r')
            else:
                including.writelines(name + '\r')

    ignoring.close()
    including.close()

    projects = set(os.listdir(source_directory))
    project_ids = set([get_item_id(folders) for folders in list(projects)])

    # check for duplicate ids
    assert_equal(len(projects), len(project_ids))


def main(files_dir, metadata_dir, id_list=None):
    """
    This is a script for our EGAP partnership that converts the EGAP provided dump of files into a directory structure
    we can easily import into the OSF. Some files in the dump are anonymous and need to be sorted into a special folder
    some don't follow an id naming convention and should be ignored and not imported.

    This script copies whole file tree for a project to preserve file hierarchy then picks out anonymous files and moves
    them to the anonymous folder and delete those that don't follow the naming convention.

    This script can be safely removed once all EGAP registrations have been imported.

    :param files_dir: the source path we're picking files out of
    :param metadata_dir: a pre-made directory structure for importing projects that we are packing files into.
    :param id_list: an optional list of project ids to limit what gets processed
    :return:
    """
    logger.info('Processing files. Source: {} Destination: {}'.format(files_dir, metadata_dir))

    project_dirs = os.listdir(files_dir)
    if id_list:
        project_dirs = [project for project in project_dirs if get_item_id(project) in id_list]

    logger.info('Processing directories: {}'.format(project_dirs))

    # Copy whole tree to preserve file hierarchy then
    for item in project_dirs:
        item_id = get_item_id(item)
        source_item = os.path.join(files_dir, item)
        destination_item = os.path.join(metadata_dir, item_id, 'data', 'nonanonymous')
        if os.path.isdir(source_item):
            copy_tree(source_item, destination_item)

    for root, directory, files in os.walk(metadata_dir):
        for item in files:
            if item not in ('project.json', 'registration-schema.json'):
                action_files_by_name(root, metadata_dir, item)

    # Check All anon files in /anonymous/ directory
    for root, directory, files in os.walk(metadata_dir):
        for item in files:
            if item not in ('project.json', 'registration-schema.json', '.DS_Store'):
                if check_anon(item):
                    assert '/anonymous' in root
                else:
                    assert '/nonanonymous' in root


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-source',
        '--source',
        help='The directory for the EGAP data files, traditionally called "EGAP_REGISTRY_staging/3 Registrations/"'
    )
    parser.add_argument(
        '-destination',
        '--destination',
        help='The directory of the import file structure containing the bags of data.'
    )
    parser.add_argument(
        '-list',
        '--list',
        help='An optional list of ids to import into a the new metadata directory.'
    )
    parser.add_argument(
        '-audit',
        '--audit',
        help='Boolean to generate two lists of all files that should and should not be included. Needs "source".'
    )

    args = parser.parse_args()
    source = args.source
    destination = args.destination
    audit = args.audit
    if audit:
        audit_files(source)
    else:
        main(source, destination)
