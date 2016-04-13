# Indices that need to be added manually:
#
# invoke shell --no-transaction

from pymongo import ASCENDING, DESCENDING


db['nodelog'].create_index([
    ('__backrefs.logged.node.logs', ASCENDING),
])

db['user'].create_index([
    ('emails', ASCENDING),
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
