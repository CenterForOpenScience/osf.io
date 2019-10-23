import os
import shutil
import argparse
from distutils.dir_util import copy_tree

get_item_id = lambda _path: _path.split(os.sep)[-1].split(' ')[0]

parser = argparse.ArgumentParser()
parser.add_argument('-source', '--source', help='')
parser.add_argument('-destination', '--destination', help='')


def main(origin_path, new_path):
    # Copy whole tree, then pick out anonymous
    for item in os.listdir(origin_path):
        item_id = get_item_id(item)
        source = os.path.join(origin_path, item)
        destination = os.path.join(origin_path, item_id, 'data', 'nonanonymous')
        copy_tree(source, destination)

    for root, dir, files in os.walk(new_path):
        for item in files:
            source = os.path.join(root, item)
            if 'PAP_anon' in item or 'Anonymous.' in item:
                destination_parent = os.path.join('/'.join(root.split('/')[:-1]), 'anonymous')
                os.mkdir(destination_parent)
                destination = os.path.join(destination_parent, item)
                shutil.move(source, destination)

    # Check All anon files in /anonymous/ direct
    for root, dir, files in os.walk(new_path):
        for item in files:
            if 'PAP_anon' in item or 'Anonymous.' in item:
                assert root.endswith('/anonymous')

    original_files = []
    moved = []

    # Check for stragglers
    for root, dir, files in os.walk(new_path):
        for item in files:
            original_files.append(item)

    for root, dir, files in os.walk(new_path):
        for item in files:
            moved.append(item)

    assert sorted(original_files) == sorted(moved)


if __name__ == '__main__':
    args = parser.parse_args()
    source = args.source
    destination = args.destination
    main(source, destination)
