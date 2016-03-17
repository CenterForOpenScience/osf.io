import logging
import sys

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

PROVIDERS = ['mendeley', 'zotero']

def migrate_list_id_field(document, provider):
    try:
        database['{}nodesettings'.format(provider)].find_and_modify(
            {'_id': document['_id']},
            {
                '$set': {
                    'list_id': document['{}_list_id'.format(provider)]
                }
            }
        )
        database['{}nodesettings'.format(provider)].find_and_modify(
            {'_id': document['_id']},
            {
                '$unset': {
                    '{}_list_id'.format(provider): ''
                }
            }
        )
    except Exception:
        return False
    return True

def verify_node_settings_document(document, provider):
    try:
        assert('_id' in document)
        assert('{}_list_id'.format(provider) in document)
    except AssertionError:
        return False
    return True

def migrate(dry_run=True):
    documents_no_list_id = {}
    documents_migration_failed = {}
    documents_migrated = {}

    for provider in PROVIDERS:
        documents_migrated[provider] = []
        documents_migration_failed[provider] = []
        documents_no_list_id[provider] = []

        for document in database['{}nodesettings'.format(provider)].find():
            if verify_node_settings_document(document, provider):
                if migrate_list_id_field(document, provider):
                    documents_migrated[provider].append(document)
                else:
                    documents_migration_failed[provider].append(document)
            else:
                documents_no_list_id[provider].append(document)

    for provider in PROVIDERS:
        if documents_migrated[provider]:
            logger.info('Successfully migrated {0} {1} node settings documents:\n{2}'.format(
                len(documents_migrated[provider]), provider, [e['_id'] for e in documents_migrated[provider]]
            ))

        if documents_no_list_id[provider]:
            logger.error('Failed to migrate {0} {1} node settings documents due to no {1}_list_id field:\n{2}'.format(
                len(documents_no_list_id[provider]), provider, [e['_id'] for e in documents_no_list_id[provider]]
            ))

        if documents_migration_failed[provider]:
            logger.error('Failed to migrate {0} {1} node settings documents for unknown reason:\n{2}'.format(
                len(documents_migration_failed[provider]), provider, [e['_id'] for e in documents_migration_failed[provider]]
            ))

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == "__main__":
    main()