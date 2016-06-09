# Indices that need to be added manually:
#
# invoke shell --no-transaction

from pymongo import ASCENDING, DESCENDING

db['storedfilenode'].create_index([
    ('tags', ASCENDING),
])

db['user'].create_index([
    ('emails', ASCENDING),
])

db['user'].create_index([
    ('external_accounts', ASCENDING),
])

db['user'].create_index([
    ('emails', ASCENDING),
    ('username', ASCENDING),
])

db['node'].create_index([
    ('is_deleted', ASCENDING),
    ('is_collection', ASCENDING),
    ('is_public', ASCENDING),
    ('institution_id', ASCENDING),
    ('is_registration', ASCENDING),
    ('contributors', ASCENDING),
])

db['node'].create_index([
    ('tags', ASCENDING),
    ('is_public', ASCENDING),
    ('is_deleted', ASCENDING),
    ('institution_id', ASCENDING),
])

# mongodb does not support indexes on parallel array's
#
# db['node'].create_index([
#     ('is_deleted', ASCENDING),
#     ('is_folder', ASCENDING),
#     ('is_registration', ASCENDING),
#     ('parent_node', ASCENDING),
#     ('is_public', ASCENDING),
#     ('contributors', ASCENDING),
#     ('_affiliated_institutions', ASCENDING),
# ])

# db['node'].create_index([
#     ('is_deleted', ASCENDING),
#     ('is_folder', ASCENDING),
#     ('is_registration', ASCENDING),
#     ('parent_node', ASCENDING),
#     ('is_public', ASCENDING),
#     ('contributors', ASCENDING),
#     ('_affiliated_institutions', ASCENDING),
#     ('date_modified', DESCENDING),
# ])
