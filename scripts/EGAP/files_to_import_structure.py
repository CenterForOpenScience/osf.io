import os
import re
import shutil
import argparse
from distutils.dir_util import copy_tree

from nose.tools import assert_equal

# This takes the item id from the path of the project directory for example '20121001AA Findley' -> '20121001AA'
get_item_id = lambda _path: _path.split(os.sep)[-1].split(' ')[0]


def action_files_by_name(root, source, item_name):
    print(root, source, item_name)
    if 'PAP_anon' in item_name or 'Anonymous.' in item_name:
        destination_parent = os.path.join('/'.join(root.split('/')[:-1]), 'anonymous')
        os.mkdir(destination_parent)
        destination = os.path.join(destination_parent, item_name)
        shutil.move(source, destination)


def audit_files(source):
    including = open('including.txt', 'w+')
    ignoring = open('ignoring.txt', 'w+')
    for root, dir, files in os.walk(source):
        for item in files:
            path = os.path.join(root.split('/')[-1], item)

            if not re.match(r'(^[0-9]{8}[A-Z]{2})', item):
                ignoring.writelines(path + '\r')
            else:
                including.writelines(path + '\r')

    ignoring.close()
    including.close()


def main(origin_path, new_path):
    # Copy whole tree, then pick out anonymous
    for item in os.listdir(origin_path):
        item_id = get_item_id(item)
        source = os.path.join(origin_path, item)
        destination = os.path.join(new_path, item_id, 'data', 'nonanonymous')
        if os.path.isdir(source):
            copy_tree(source, destination)

    for root, dir, files in os.walk(new_path):
        for item in files:
            source = os.path.join(root, item)
            action_files_by_name(root, source, item)

    # Check All anon files in /anonymous/ directory
    for root, dir, files in os.walk(new_path):
        for item in files:
            if 'PAP_anon' in item or 'Anonymous.' in item:
                assert root.endswith('/anonymous')
            else:
                assert root.endswith('/nonanonymous')

    original_files = []
    moved = []

    # Check for stragglers
    for root, dir, files in os.walk(new_path):
        for item in files:
            original_files.append(item)

    for root, dir, files in os.walk(new_path):
        for item in files:
            moved.append(item)

    assert assert_equal(sorted(original_files), sorted(moved))


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
        '-audit',
        '--audit',
        help='This includes all files that don\'t follow the "<id>_PAP" naming convention .'
    )

    args = parser.parse_args()
    source = args.source
    destination = args.destination
    audit = args.audit
    if audit:
        audit_files(source)
    else:
        main(source, destination)
