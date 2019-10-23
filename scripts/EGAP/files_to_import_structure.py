import os
import shutil
from distutils.dir_util import copy_tree
BASE_PATH = 'EGAP_REGISTRY_staging/3 Registrations/'
NEW_PATH = 'EGAP_data_10-22-2019'
get_item_id = lambda _path: _path.split(os.sep)[-1].split(' ')[0]

# Copy whole tree, then pick out anonymous
for item in os.listdir(BASE_PATH):
    item_id = get_item_id(item)
    source = os.path.join(BASE_PATH, item)
    destination = os.path.join(NEW_PATH, item_id, 'data', 'nonanonymous')
    copy_tree(source, destination)

for root, dir, files in os.walk(NEW_PATH):
    for item in files:
        source = os.path.join(root, item)
        if 'PAP_anon' in item or 'Anonymous.' in item:
            destination_parent = os.path.join('/'.join(root.split('/')[:-1]), 'anonymous')
            os.mkdir(destination_parent)
            destination = os.path.join(destination_parent, item)
            shutil.move(source, destination)


# Check All anon files in /anonymous/ direct
for root, dir, files in os.walk(NEW_PATH):
    for item in files:
        if 'PAP_anon' in item or 'Anonymous.' in item:
            assert root.endswith('/anonymous')

original_files = []
moved = []

# Check for stragglers
for root, dir, files in os.walk(NEW_PATH):
    for item in files:
        original_files.append(item)

for root, dir, files in os.walk(NEW_PATH):
    for item in files:
        moved.append(item)

assert sorted(original_files) == sorted(moved)
