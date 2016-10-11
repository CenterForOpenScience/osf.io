from datetime import timedelta
import logging
import sys

from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website import models 

logger = logging.getLogger(__name__)


def get_targets():
    return database.node.find({'preprint_file': {'$ne': None}})

def validate_node_document(document):
    logger.info('* Validating and repairing node {}'.format(document['_id']))    

    assert document.get('preprint_created'), '{} has no preprint_created'.format(document['_id'])
    assert document.get('preprint_file'), '{} has no preprint_file'.format(document['_id'])
    assert document.get('preprint_subjects'), '{} has no preprint_subjects'.format(document['_id'])

    if not document.get('preprint_providers'):
        logger.debug('{} has no preprint_providers, assuming OSF'.format(document['_id']))
        database['node'].find_and_modify(
            {'_id': document['_id']},
            {'$set': {
                'preprint_providers': ['osf']
            }}
        )

def validate_node_preprint_subjects(node):
    flat_subjects = node.preprint_subjects
    for subject_id in flat_subjects:
        subject = models.Subject.load(subject_id)
        if not subject:
            logger.debug('Found nonexistant subject {} on node {}, removing'.format(subject_id, node._id))
            node.preprint_subjects.remove(subject_id)
            node.save()
            validate_node_preprint_subjects(node)
            break
        if subject.parents and not set([c._id for c in subject.parents]) & set(flat_subjects):
            logger.debug('Found subject {} on node {} without parents. Adding first parent - {}'.format(subject_id, node._id, subject.parents[0]._id))
            node.preprint_subjects.append(subject.parents[0]._id)
            node.save()
            validate_node_preprint_subjects(node)
            break


def create_preprint_service_from_node(document, swap_cutoff):
    created = {}
    for provider_id in document['preprint_providers']:
        node = models.Node.load(document['_id'])
        provider = models.PreprintProvider.load(provider_id)
        # primary_file already set correctly* on node
        if not provider:
            logger.warn('Unable to find provider {} for node {}, skipping'.format(provider_id, document['_id']))
            continue

        try:
            logger.info('* Creating preprint for node {}'.format(node._id))
            preprint = models.PreprintService(node=node, provider=provider)
            preprint.save()
            database['preprintservice'].find_and_modify(
                {'_id': preprint._id},
                {'$set': {
                    'date_created': document['preprint_created'],
                    'date_published': document['preprint_created'],
                    'is_published': True
                }}
            )
        except KeyExistsException:
            logger.warn('Duplicate PreprintService found for provider {} on node {}, skipping'.format(provider._id, node._id))
            continue
        else:
            if preprint.provider._id == 'osf':
                # Give Guid retention priotity to OSF-provider
                # Probably won't matter; shouldn't be non-osf
                if should_swap_guids(node, preprint, swap_cutoff):
                    swap_guids(node, preprint)
                else:
                    logger.info('* Not swapping guids for preprint {} and preexisting node {}'.format(preprint._id, node._id))
            node.reload()
            preprint.reload()
            validate_node_preprint_subjects(preprint.node)
            preprint.node.reload()
            enumerate_and_set_subject_hierarchies(preprint)
            created.update({preprint._id: node._id})

    return created

def should_swap_guids(node, preprint, swap_cutoff):
    preprint.reload()
    logger.info('Preprint {} - Node {} timedelta = {}'.format(preprint._id, node._id, preprint.date_created - node.date_created))
    return preprint.date_created - node.date_created < swap_cutoff

def swap_guids(node, preprint):
    logger.info('* Swapping guids for preprint {} and node {}'.format(preprint._id, node._id))    
    old_guid = models.Guid.load(node._id)
    new_guid = models.Guid.load(preprint._id)
    node._id = new_guid._id
    node.save()
    preprint._id = old_guid._id
    preprint.node = node
    preprint.save()
    old_guid.referent = preprint
    new_guid.referent = node
    old_guid.save()
    new_guid.save()
    update_foreign_fields(old_guid._id, node)


def update_foreign_fields(old_id, node):
    dry_run = '--dry' in sys.argv
    logger.info('* Updating ForeignFields for node {}->{}'.format(old_id, node))

    if dry_run:
        # Check iff dry for efficiency
        assert database['boxnodesettings'].find().count(), 'Unable to find collection boxnodesettings'    
    if database['boxnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating BoxNodeSettings {}'.format([d['_id'] for d in database['boxnodesettings'].find({'owner': old_id})]))
        database['boxnodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['addondataversenodesettings'].find().count(), 'Unable to find collection addondataversenodesettings'
    if database['addondataversenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonDataverseNodeSettings {}'.format([d['_id'] for d in database['addondataversenodesettings'].find({'owner': old_id})]))
        database['addondataversenodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['dropboxnodesettings'].find().count(), 'Unable to find collection dropboxnodesettings'
    if database['dropboxnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating DropboxNodeSettings {}'.format([d['_id'] for d in database['dropboxnodesettings'].find({'owner': old_id})]))
        database['dropboxnodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['addonfigsharenodesettings'].find().count(), 'Unable to find collection addonfigsharenodesettings'
    if database['addonfigsharenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonFigShareNodeSettings {}'.format([d['_id'] for d in database['addonfigsharenodesettings'].find({'owner': old_id})]))
        database['addonfigsharenodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['forwardnodesettings'].find().count(), 'Unable to find collection forwardnodesettings'
    if database['forwardnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating ForwardNodeSettings {}'.format([d['_id'] for d in database['forwardnodesettings'].find({'owner': old_id})]))
        database['forwardnodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['githubnodesettings'].find().count(), 'Unable to find collection githubnodesettings'
    if database['githubnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating GithubNodeSettings {}'.format([d['_id'] for d in database['githubnodesettings'].find({'owner': old_id})]))
        database['githubnodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['mendeleynodesettings'].find().count(), 'Unable to find collection mendeleynodesettings'
    if database['mendeleynodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating MendeleyNodeSettings {}'.format([d['_id'] for d in database['mendeleynodesettings'].find({'owner': old_id})]))
        database['mendeleynodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['osfstoragenodesettings'].find().count(), 'Unable to find collection osfstoragenodesettings'
    if database['osfstoragenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating OsfStorageNodeSettings {}'.format([d['_id'] for d in database['osfstoragenodesettings'].find({'owner': old_id})]))
        database['osfstoragenodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['s3nodesettings'].find().count(), 'Unable to find collection s3nodesettings'
    if database['s3nodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating s3NodeSettings {}'.format([d['_id'] for d in database['s3nodesettings'].find({'owner': old_id})]))
        database['s3nodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['addonwikinodesettings'].find().count(), 'Unable to find collection addonwikinodesettings'
    if database['addonwikinodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonWikiNodeSettings {}'.format([d['_id'] for d in database['addonwikinodesettings'].find({'owner': old_id})]))
        database['addonwikinodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['zoteronodesettings'].find().count(), 'Unable to find collection zoteronodesettings'
    if database['zoteronodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating ZoteroNodeSettings {}'.format([d['_id'] for d in database['zoteronodesettings'].find({'owner': old_id})]))
        database['zoteronodesettings'].update(
            {'owner': old_id},
            {'$set':{
                'owner': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['archivejob'].find().count(), 'Unable to find collection archivejob'
    if database['archivejob'].find({'src_node': old_id}).count():
        logger.info('** Updating ArchiveJobs {}'.format([d['_id'] for d in database['archivejob'].find({'src_node': old_id})]))
        database['archivejob'].update(
            {'src_node': old_id},
            {'$set':{
                'src_node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['trashedfilenode'].find().count(), 'Unable to find collection trashedfilenode'
    if database['trashedfilenode'].find({'node': old_id}).count():
        logger.info('** Updating TrashedFileNodes {}'.format([d['_id'] for d in database['trashedfilenode'].find({'node': old_id})]))
        database['trashedfilenode'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['storedfilenode'].find().count(), 'Unable to find collection storedfilenode'
    if database['storedfilenode'].find({'node': old_id}).count():
        logger.info('** Updating StoredFileNodes {}'.format([d['_id'] for d in database['storedfilenode'].find({'node': old_id})]))
        database['storedfilenode'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['comment'].find().count(), 'Unable to find collection comment'
    if database['comment'].find({'node': old_id}).count():
        logger.info('** Updating Comments {}'.format([d['_id'] for d in database['comment'].find({'node': old_id})]))
        database['comment'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['nodelog'].find().count(), 'Unable to find collection nodelog'
    if database['nodelog'].find({'original_node': old_id}).count():
        logger.info('** Updating NodeLogs (original_node) {}'.format([d['_id'] for d in database['nodelog'].find({'original_node': old_id})]))
        database['nodelog'].update(
            {'original_node': old_id},
            {'$set':{
                'original_node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['nodelog'].find().count(), 'Unable to find collection nodelog'
    if database['nodelog'].find({'node': old_id}).count():
        logger.info('** Updating NodeLogs (node) {}'.format([d['_id'] for d in database['nodelog'].find({'node': old_id})]))
        database['nodelog'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['pointer'].find().count(), 'Unable to find collection pointer'
    if database['pointer'].find({'node': old_id}).count():
        logger.info('** Updating Pointers {}'.format([d['_id'] for d in database['pointer'].find({'node': old_id})]))
        database['pointer'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['node'].find().count(), 'Unable to find collection node'
    if database['node'].find({'forked_from': old_id}).count():
        logger.info('** Updating Nodes (forked_from) {}'.format([d['_id'] for d in database['node'].find({'forked_from': old_id})]))
        database['node'].update(
            {'forked_from': old_id},
            {'$set':{
                'forked_from': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['node'].find().count(), 'Unable to find collection node'
    if database['node'].find({'registered_from': old_id}).count():
        logger.info('** Updating Nodes (registered_from) {}'.format([d['_id'] for d in database['node'].find({'registered_from': old_id})]))
        database['node'].update(
            {'registered_from': old_id},
            {'$set':{
                'registered_from': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['node'].find().count(), 'Unable to find collection node'
    if database['node'].find({'root': old_id}).count():
        logger.info('** Updating Nodes (root) {}'.format([d['_id'] for d in database['node'].find({'root': old_id})]))
        database['node'].update(
            {'root': old_id},
            {'$set':{
                'root': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['node'].find().count(), 'Unable to find collection node'
    if database['node'].find({'parent': old_id}).count():
        logger.info('** Updating Nodes (parent) {}'.format([d['_id'] for d in database['node'].find({'parent': old_id})]))
        database['node'].update(
            {'parent': old_id},
            {'$set':{
                'parent': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['watchconfig'].find().count(), 'Unable to find collection watchconfig'
    if database['watchconfig'].find({'node': old_id}).count():
        logger.info('** Updating WatchConfigs {}'.format([d['_id'] for d in database['watchconfig'].find({'node': old_id})]))
        database['watchconfig'].update(
            {'node': old_id},
            {'$set':{
                'node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['privatelink'].find().count(), 'Unable to find collection privatelink'
    if database['privatelink'].find({'nodes': old_id}).count():
        pls = database['privatelink'].find({'nodes': old_id})
        logger.info('** Updating PrivateLinks {}'.format([d['_id'] for d in pls]))
        for d in pls:
            new_nodes = d['nodes']
            new_nodes.remove(old_id)
            new_nodes.append(node._id) 
            database['privatelink'].find_and_modify(
                {'_id': d['_id']},
                {'$set':{
                    'nodes': new_nodes
                }}
            )

    if dry_run:
        # Check iff dry for efficiency
        assert database['draftregistration'].find().count(), 'Unable to find collection draftregistration'
    if database['draftregistration'].find({'branched_from': old_id}).count():
        logger.info('** Updating DraftRegistrations {}'.format([d['_id'] for d in database['draftregistration'].find({'branched_from': old_id})]))
        database['draftregistration'].update(
            {'branched_from': old_id},
            {'$set':{
                'branched_from': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['draftregistration'].find().count(), 'Unable to find collection draftregistration'
    if database['draftregistration'].find({'registered_node': old_id}).count():
        logger.info('** Updating DraftRegistrations {}'.format([d['_id'] for d in database['draftregistration'].find({'registered_node': old_id})]))
        database['draftregistration'].update(
            {'registered_node': old_id},
            {'$set':{
                'registered_node': node._id
            }}
        )

    if dry_run:
        # Check iff dry for efficiency
        assert database['embargoterminationapproval'].find().count(), 'Unable to find collection embargoterminationapproval'
    if database['embargoterminationapproval'].find({'embargoed_registration': old_id}).count():
        logger.info('** Updating EmbargoTerminationApprovals {}'.format([d['_id'] for d in database['embargoterminationapproval'].find({'embargoed_registration': old_id})]))
        database['embargoterminationapproval'].update(
            {'embargoed_registration': old_id},
            {'$set':{
                'embargoed_registration': node._id
            }}
        )

def enumerate_and_set_subject_hierarchies(preprint):
    logger.info('* Migrating subjects for node {}'.format(preprint.node._id))
    hierarchical_subjects, flat_subjects = [], set(preprint.node.preprint_subjects)
    for subject_id in preprint.node.preprint_subjects:
        subject = models.Subject.load(subject_id)
        if set([c._id for c in subject.children]) & flat_subjects:
            continue

        trees = [(subject, )]
        while trees:
            tree = trees.pop(0)
            if not tree[0].parents:
                hierarchical_subjects.append([s._id for s in tree])
            else:
                trees.extend([(p, ) + tree for p in tree[0].parents if p._id in flat_subjects])
    assert set(flat_subjects) == set(sum(hierarchical_subjects, [])), \
        'Flat subject set `{}` not equal to hierarchical subject set `{}`'.format(flat_subjects, hierarchical_subjects)
    preprint.subjects = hierarchical_subjects
    preprint.save()

def migrate(swap_cutoff):
    database['node'].update({'preprint_doi': {'$type': 2}}, {'$rename': { 'preprint_doi': 'article_doi'}}, multi=True)

    target_documents = list(get_targets())
    target_ids = [d['_id'] for d in target_documents]
    target_count = len(target_documents)
    successes = []
    failures = []
    created_preprints = []

    logger.info('Preparing to migrate {} preprint nodes.'.format(target_count))
    logger.info('Cutoff delta for swapping guids is {} seconds'.format(swap_cutoff.total_seconds()))
    for node in target_documents:
        validate_node_document(node)
        node = database['node'].find({'_id': node['_id']})[0]  # .reload()
        preprints = create_preprint_service_from_node(node, swap_cutoff)
        if not preprints:
            failures.append(node['_id'])
            logger.error('({}-{}/{}) Failed to create any PreprintServices for node {}'.format(
                len(successes),
                len(failures),
                target_count, 
                node['_id'])
            )
        else:
            for preprint_id in preprints:
                created_preprints.append(preprint_id)
            successes.append(node['_id'])
            logger.info('({}-{}/{}) Successfully migrated {}'.format(
                len(successes),
                len(failures),
                target_count, 
                node['_id']
                )
            )

    logger.info('Preprints with new _ids: {}'.format(list(set(created_preprints)-set(target_ids))))
    logger.info('Successes: {}'.format(successes))
    logger.info('Failures: {}'.format(failures))
    logger.info('Missed nodes: {}'.format(list(set(target_ids)-set(successes + failures))))
    logger.info('Created {} preprints from {} nodes'.format(len(created_preprints), target_count))


def main():
    dry_run = '--dry' in sys.argv
    td = timedelta()
    if '--minutes' in sys.argv:
        td += timedelta(minutes=int(sys.argv[1 + sys.argv.index('--minutes')]))
    if '--hours' in sys.argv:
        td += timedelta(hours=int(sys.argv[1 + sys.argv.index('--hours')]))
    if td.total_seconds() == 0:
        td += timedelta(hours=1)
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(swap_cutoff=td)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
