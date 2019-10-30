import os
import re
import shutil
import argparse
from distutils.dir_util import copy_tree

from nose.tools import assert_equal

# This takes the item id from the path of the project directory for example '20121001AA Findley' -> '20121001AA'
get_item_id = lambda _path: _path.split(os.sep)[-1].split(' ')[0]


# Check if file name starts with EGAP id for example '20121001AA_PAP.pdf'
def check_id(root, item):
    project_id = get_item_id(root.split('/')[-3])
    return item.startswith(project_id)


# Check if file follows anonymous naming convention
check_anon = lambda item: 'pap_anon' in item.lower() or 'anonymous' in item.lower()


def action_files_by_name(root, source, item_name):
    """
    Pick out anonymous and create new folder to move them into it, remove ones that don't follow id naming convention.
    :param root:
    :param source:
    :param item_name:
    :return:
    """
    if not check_id(root, item_name):
        path = os.path.join(root, item_name)
        os.remove(path)
        return

    if check_anon(item_name):
        destination_parent = os.path.join('/'.join(root.split('/')[:-1]), 'anonymous')

        if not os.path.exists(destination_parent):
            os.mkdir(destination_parent)

        destination = os.path.join(destination_parent, item_name)
        shutil.move(source, destination)


def audit_files(source):
    including = open('including.txt', 'w+')
    ignoring = open('ignoring.txt', 'w+')
    for root, dir, files in os.walk(source):
        for item in files:
            name = os.path.join(root.split('/')[-1], item) # get file/folder name after slash
            if not check_id(root, name):
                ignoring.writelines(name + '\r')
            else:
                including.writelines(name + '\r')

    ignoring.close()
    including.close()

    projects = set(os.listdir(source))
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
    :return:
    """
    project_dirs = os.listdir(files_dir)
    if id_list:
        project_dirs = [project for project in project_dirs if get_item_id(project) in id_list]

    # Copy whole tree to preserve file hierarchy then
    for item in project_dirs:
        item_id = get_item_id(item)
        source = os.path.join(files_dir, item)
        destination = os.path.join(metadata_dir, item_id, 'data', 'nonanonymous')
        if os.path.isdir(source):
            copy_tree(source, destination)

    for root, dir, files in os.walk(metadata_dir):
        for item in files:
            if item not in ('project.json', 'registration-schema.json'):
                source = os.path.join(root, item)
                action_files_by_name(root, source, item)

    # Check All anon files in /anonymous/ directory
    for root, dir, files in os.walk(metadata_dir):
        for item in files:
            if item not in ('project.json', 'registration-schema.json'):
                if check_anon(item):
                    assert '/anonymous' in root
                else:
                    assert '/nonanonymous' in root


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-source',
        '--source',
        help='This should be the directory for the EGAP data dump, traditionally called "EGAP_REGISTRY_staging/3 Registrations/"'
    )
    parser.add_argument(
        '-destination',
        '--destination',
        help='This should be the directory of the import file structure containing the bags of data.'
    )
    parser.add_argument(
        '-list',
        '--list',
        help='This is a list of ids to import into a the new metadata directory.'
    )
    parser.add_argument(
        '-audit',
        '--audit',
        help='This includes all files that don\'t follow the "<id>_PAP" naming convention.'
    )

    args = parser.parse_args()
    source = args.source
    destination = args.destination
    audit = args.audit
    if audit:
        audit_files(source)
    else:
        main(source, destination)
