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
from website import settings

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
        non_osf_provider = False
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
            if node.preprint_doi:
                database['node'].find_and_modify(
                    {'_id': node._id},
                    {'$set': {
                        'preprint_article_doi': document['preprint_doi']
                    }}
                )
            database['node'].find_and_modify(
                {'_id': node._id},
                {'$unset': {
                    'preprint_doi': '',
                    'preprint_created': ''
                }}
            )
            if preprint.provider._id == 'osf':
                # Give Guid retention priotity to OSF-provider
                if should_swap_guids(node, preprint, swap_cutoff):
                    swap_guids(node, preprint)
                else:
                    logger.info('* Not swapping guids for preprint {} and preexisting node {}'.format(preprint._id, node._id))
            else:
                logger.info('* Not swapping guids for preprint {} for provider {}'.format(preprint._id, preprint.provider))
                non_osf_provider = True
            node.reload()
            preprint.reload()
            validate_node_preprint_subjects(preprint.node)
            preprint.node.reload()
            enumerate_and_set_subject_hierarchies(preprint)
            created.update({preprint._id: (node._id, non_osf_provider)})

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

    if database['boxnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating BoxNodeSettings {}'.format([d['_id'] for d in database['boxnodesettings'].find({'owner': old_id})]))
        for doc in database['boxnodesettings'].find({'owner': old_id}):
            database['boxnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['boxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating BoxUserSettings {}'.format([d['_id'] for d in database['boxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['boxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['boxusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['addondataversenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonDataverseNodeSettings {}'.format([d['_id'] for d in database['addondataversenodesettings'].find({'owner': old_id})]))
        for doc in database['addondataversenodesettings'].find({'owner': old_id}):
            database['addondataversenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['addondataverseusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating AddonDataverseUserSettings {}'.format([d['_id'] for d in database['addondataverseusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['addondataverseusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['addondataverseusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['dropboxnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating DropboxNodeSettings {}'.format([d['_id'] for d in database['dropboxnodesettings'].find({'owner': old_id})]))
        for doc in database['dropboxnodesettings'].find({'owner': old_id}):
            database['dropboxnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['dropboxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating DropboxUserSettings {}'.format([d['_id'] for d in database['dropboxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['dropboxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['dropboxusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['addonfigsharenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonFigShareNodeSettings {}'.format([d['_id'] for d in database['addonfigsharenodesettings'].find({'owner': old_id})]))
        for doc in database['addonfigsharenodesettings'].find({'owner': old_id}):
            database['addonfigsharenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ## Figshare has no oauth_grants

    if database['forwardnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating ForwardNodeSettings {}'.format([d['_id'] for d in database['forwardnodesettings'].find({'owner': old_id})]))
        for doc in database['forwardnodesettings'].find({'owner': old_id}):
            database['forwardnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['githubnodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating GithubNodeSettings {}'.format([d['_id'] for d in database['githubnodesettings'].find({'owner': old_id})]))
        for doc in database['githubnodesettings'].find({'owner': old_id}):
            database['githubnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['githubusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating GithubUserSettings {}'.format([d['_id'] for d in database['githubusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['githubusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['githubusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['googledrivenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating GoogleDriveNodeSettings {}'.format([d['_id'] for d in database['googledrivenodesettings'].find({'owner': old_id})]))
        for doc in database['googledrivenodesettings'].find({'owner': old_id}):
            database['googledrivenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['googledriveusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating GoogleDriveUserSettings {}'.format([d['_id'] for d in database['googledriveusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['googledriveusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['googledriveusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['mendeleynodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating MendeleyNodeSettings {}'.format([d['_id'] for d in database['mendeleynodesettings'].find({'owner': old_id})]))
        for doc in database['mendeleynodesettings'].find({'owner': old_id}):
            database['mendeleynodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['mendeleyusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating MendeleyUserSettings {}'.format([d['_id'] for d in database['mendeleyusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['mendeleyusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['mendeleyusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['osfstoragenodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating OsfStorageNodeSettings {}'.format([d['_id'] for d in database['osfstoragenodesettings'].find({'owner': old_id})]))
        for doc in database['osfstoragenodesettings'].find({'owner': old_id}):
            database['osfstoragenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['s3nodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating s3NodeSettings {}'.format([d['_id'] for d in database['s3nodesettings'].find({'owner': old_id})]))
        for doc in database['s3nodesettings'].find({'owner': old_id}):
            database['s3nodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['s3usersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating S3UserSettings {}'.format([d['_id'] for d in database['s3usersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['s3usersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['s3usersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['addonwikinodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating AddonWikiNodeSettings {}'.format([d['_id'] for d in database['addonwikinodesettings'].find({'owner': old_id})]))
        for doc in database['addonwikinodesettings'].find({'owner': old_id}):
            database['addonwikinodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['zoteronodesettings'].find({'owner': old_id}).count():
        logger.info('** Updating ZoteroNodeSettings {}'.format([d['_id'] for d in database['zoteronodesettings'].find({'owner': old_id})]))
        for doc in database['zoteronodesettings'].find({'owner': old_id}):
            database['zoteronodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    if database['zoterousersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating ZoteroUserSettings {}'.format([d['_id'] for d in database['zoterousersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['zoterousersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}):
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['zoterousersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    if database['archivejob'].find({'src_node': old_id}).count():
        logger.info('** Updating ArchiveJobs {}'.format([d['_id'] for d in database['archivejob'].find({'src_node': old_id})]))
        for doc in database['archivejob'].find({'src_node': old_id}):
            database['archivejob'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'src_node': node._id
                }}
            )

    if database['trashedfilenode'].find({'node': old_id}).count():
        logger.info('** Updating TrashedFileNodes {}'.format([d['_id'] for d in database['trashedfilenode'].find({'node': old_id})]))
        for doc in database['trashedfilenode'].find({'node': old_id}):
            database['trashedfilenode'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    if database['storedfilenode'].find({'node': old_id}).count():
        logger.info('** Updating StoredFileNodes {}'.format([d['_id'] for d in database['storedfilenode'].find({'node': old_id})]))
        for doc in database['storedfilenode'].find({'node': old_id}):
            database['storedfilenode'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    if database['comment'].find({'node': old_id}).count():
        logger.info('** Updating Comments {}'.format([d['_id'] for d in database['comment'].find({'node': old_id})]))
        for doc in database['comment'].find({'node': old_id}):
            database['comment'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    if database['nodelog'].find({'original_node': old_id}).count():
        logger.info('** Updating NodeLogs (original_node) {}'.format([d['_id'] for d in database['nodelog'].find({'original_node': old_id})]))
        for doc in database['nodelog'].find({'original_node': old_id}):
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'original_node': node._id
                }}
            )
    if database['nodelog'].find({'node': old_id}).count():
        logger.info('** Updating NodeLogs (node) {}'.format([d['_id'] for d in database['nodelog'].find({'node': old_id})]))
        for doc in database['nodelog'].find({'node': old_id}):
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )
    if database['nodelog'].find({'params.node': old_id}).count():
        logger.info('** Updating NodeLogs (params.node) {}'.format([d['_id'] for d in database['nodelog'].find({'params.node': old_id})]))
        for doc in database['nodelog'].find({'params.node': old_id}):
            params = doc['params']
            params['node'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.parent': old_id}).count():
        logger.info('** Updating NodeLogs (params.parent) {}'.format([d['_id'] for d in database['nodelog'].find({'params.parent': old_id})]))
        for doc in database['nodelog'].find({'parent': old_id}):
            params = doc['params']
            params['parent'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.project': old_id}).count():
        logger.info('** Updating NodeLogs (params.project) {}'.format([d['_id'] for d in database['nodelog'].find({'params.project': old_id})]))
        for doc in database['nodelog'].find({'project': old_id}):
            params = doc['params']
            params['project'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.parent_node': old_id}).count():
        logger.info('** Updating NodeLogs (params.parent_node) {}'.format([d['_id'] for d in database['nodelog'].find({'params.parent_node': old_id})]))
        for doc in database['nodelog'].find({'params.parent_node': old_id}):
            params = doc['params']
            params['parent_node'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.destination.nid': old_id}).count():
        logger.info('** Updating NodeLogs (params.destination.nid) {}'.format([d['_id'] for d in database['nodelog'].find({'params.destination.nid': old_id})]))
        for doc in database['nodelog'].find({'params.destination.nid': old_id}):
            params = doc['params']
            params['destination']['nid'] = node._id
            if params['destination'].get('url', None):
                params['destination']['url'] = params['destination']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.destination.node._id': old_id}).count():
        logger.info('** Updating NodeLogs (params.destination.node._id) {}'.format([d['_id'] for d in database['nodelog'].find({'params.destination.node._id': old_id})]))
        for doc in database['nodelog'].find({'params.destination.node._id': old_id}):
            params = doc['params']
            params['destination']['node']['_id'] = node._id
            if params['destination']['node'].get('url', None):
                params['destination']['node']['url'] = params['destination']['node']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.pointer._id': old_id}).count():
        logger.info('** Updating NodeLogs (params.pointer._id) {}'.format([d['_id'] for d in database['nodelog'].find({'params.pointer._id': old_id})]))
        for doc in database['nodelog'].find({'params.pointer._id': old_id}):
            params = doc['params']
            params['pointer']['_id'] = node._id
            if params['pointer'].get('url', None):
                params['pointer']['url'] = params['pointer']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.source.nid': old_id}).count():
        logger.info('** Updating NodeLogs (params.source.nid) {}'.format([d['_id'] for d in database['nodelog'].find({'params.source.nid': old_id})]))
        for doc in database['nodelog'].find({'params.source.nid': old_id}):
            params = doc['params']
            params['source']['nid'] = node._id
            if params['source'].get('url', None):
                params['source']['url'] = params['source']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.source.node._id': old_id}).count():
        logger.info('** Updating NodeLogs (params.source.node._id) {}'.format([d['_id'] for d in database['nodelog'].find({'params.source.node._id': old_id})]))
        for doc in database['nodelog'].find({'params.source.node._id': old_id}):
            params = doc['params']
            params['source']['node']['_id'] = node._id
            if params['source']['node'].get('url', None):
                params['source']['node']['url'] = params['source']['node']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.template_node._id': old_id}).count():
        logger.info('** Updating NodeLogs (params.template_node._id) {}'.format([d['_id'] for d in database['nodelog'].find({'params.template_node._id': old_id})]))
        for doc in database['nodelog'].find({'params.template_node._id': old_id}):
            params = doc['params']
            params['template_node']['_id'] = node._id
            if params['template_node'].get('url', None):
                params['template_node']['url'] = params['template_node']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )
    if database['nodelog'].find({'params.urls.download': {'$regex': '/{}/'.format(old_id)}}).count():
        docs = list(database['nodelog'].find({'params.urls.download': {'$regex': '/{}/'.format(old_id)}}))
        logger.info('** Updating NodeLogs (params.source.node._id) {}'.format([d['_id'] for d in docs]))
        for doc in docs:
            params = doc['params']
            params['urls']['download'] = params['urls']['download'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            if params['urls'].get('view', None):
                params['urls']['view'] = params['urls']['view'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    if database['pointer'].find({'node': old_id}).count():
        logger.info('** Updating Pointers {}'.format([d['_id'] for d in database['pointer'].find({'node': old_id})]))
        for doc in database['pointer'].find({'node': old_id}):
            database['pointer'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    if database['node'].find({'forked_from': old_id}).count():
        logger.info('** Updating Nodes (forked_from) {}'.format([d['_id'] for d in database['node'].find({'forked_from': old_id})]))
        for doc in database['node'].find({'forked_from': old_id}):
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'forked_from': node._id
                }}
            )

    if database['node'].find({'registered_from': old_id}).count():
        logger.info('** Updating Nodes (registered_from) {}'.format([d['_id'] for d in database['node'].find({'registered_from': old_id})]))
        for doc in database['node'].find({'registered_from': old_id}):
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'registered_from': node._id
                }}
            )

    if database['node'].find({'root': old_id}).count():
        logger.info('** Updating Nodes (root) {}'.format([d['_id'] for d in database['node'].find({'root': old_id})]))
        for doc in database['node'].find({'root': old_id}):
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'root': node._id
                }}
            )

    if database['node'].find({'parent': old_id}).count():
        logger.info('** Updating Nodes (parent) {}'.format([d['_id'] for d in database['node'].find({'parent': old_id})]))
        for doc in database['node'].find({'parent': old_id}):
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'parent': node._id
                }}
            )

    if database['node'].find({'$where': 'var keys=Object.keys(this.child_node_subscriptions);for(var i=0;i<keys.length;i+=1){{if(this.child_node_subscriptions[keys[i]].indexOf("{}")!==-1){{return true}}}}return false;'.format(old_id)}).count():
        docs = list(database['node'].find({'$where': 'var keys=Object.keys(this.child_node_subscriptions);for(var i=0;i<keys.length;i+=1){{if(this.child_node_subscriptions[keys[i]].indexOf("{}")!==-1){{return true}}}}return false;'.format(old_id)}))
        logger.info('** Updating Nodes (child_node_subscriptions) {}'.format([d['_id'] for d in docs]))
        for doc in docs:
            cns = doc['child_node_subscriptions']
            for uid in cns:
                if old_id in cns[uid]:
                    cns[uid].insert(cns[uid].index(old_id), node._id)
                    cns[uid].remove(old_id)
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'child_node_subscriptions': cns
                }}
            )


    if database['notificationdigest'].find({'node_lineage': {'$in': [old_id]}}).count():
        logger.info('** Updating NotificationDigest {}'.format([d['_id'] for d in database['notificationdigest'].find({'node_lineage': {'$in': [old_id]}})]))
        for doc in database['notificationdigest'].find({'node_lineage': {'$in': [old_id]}}):
            nl = doc['node_lineage']
            nl.insert(nl.index(old_id), node._id)
            nl.remove(old_id)
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node_lineage': nl
                }}
            )

    if database['notificationsubscription'].find({'owner': {'$in': [old_id]}}).count():
        logger.info('** Updating NotificationSubscription (owner) {}'.format([d['_id'] for d in database['notificationsubscription'].find({'node_lineage': {'$in': [old_id]}})]))
        for doc in database['notificationsubscription'].find({'owner': {'$in': [old_id]}}):
            owner = doc['owner']
            owner.insert(owner.index(old_id), node._id)
            owner.remove(old_id)
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': owner
                }}
            )

    if database['notificationsubscription'].find({'_id': {'$regex': old_id}}).count():
        docs = list(database['notificationsubscription'].find({'_id': {'$regex': old_id}}))
        logger.info('** Updating NotificationSubscription (_id) {}'.format([d['_id'] for d in docs]))
        for doc in docs:
            _id = doc['_id']
            _id.replace(old_id, node._id)
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    '_id': _id
                }}
            )

    if database['user'].find({'unclaimed_records.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating Users (unclaimed_records) {}'.format([d['_id'] for d in database['user'].find({'unclaimed_records.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['user'].find({'unclaimed_records.{}'.format(old_id): {'$ne': None}}):
            ucr = doc['unclaimed_records']
            ucr[node._id] = ucr.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'unclaimed_records': ucr
                }}
            )
    if database['user'].find({'contributor_added_email_records.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating Users (contributor_added_email_records) {}'.format([d['_id'] for d in database['user'].find({'contributor_added_email_records.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['user'].find({'contributor_added_email_records.{}'.format(old_id): {'$ne': None}}):
            caer = doc['contributor_added_email_records']
            caer[node._id] = caer.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'contributor_added_email_records': caer
                }}
            )
    if database['user'].find({'notifications_configured.{}'.format(old_id): {'$ne': None}}).count():
        logger.info('** Updating Users (notifications_configured) {}'.format([d['_id'] for d in database['user'].find({'notifications_configured.{}'.format(old_id): {'$ne': None}})]))
        for doc in database['user'].find({'notifications_configured.{}'.format(old_id): {'$ne': None}}):
            nc = doc['notifications_configured']
            nc[node._id] = nc.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'notifications_configured': nc
                }}
            )

    if database['watchconfig'].find({'node': old_id}).count():
        logger.info('** Updating WatchConfigs {}'.format([d['_id'] for d in database['watchconfig'].find({'node': old_id})]))
        for doc in database['watchconfig'].find({'node': old_id}):
            database['watchconfig'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

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

    if database['draftregistration'].find({'branched_from': old_id}).count():
        logger.info('** Updating DraftRegistrations {}'.format([d['_id'] for d in database['draftregistration'].find({'branched_from': old_id})]))
        for doc in database['draftregistration'].find({'branched_from': old_id}):
            database['draftregistration'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'branched_from': node._id
                }}
            )

    if database['draftregistration'].find({'registered_node': old_id}).count():
        logger.info('** Updating DraftRegistrations {}'.format([d['_id'] for d in database['draftregistration'].find({'registered_node': old_id})]))
        for doc in database['draftregistration'].find({'registered_node': old_id}):
            database['draftregistration'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'registered_node': node._id
                }}
            )

    if database['embargoterminationapproval'].find({'embargoed_registration': old_id}).count():
        logger.info('** Updating EmbargoTerminationApprovals {}'.format([d['_id'] for d in database['embargoterminationapproval'].find({'embargoed_registration': old_id})]))
        for doc in database['embargoterminationapproval'].find({'embargoed_registration': old_id}):
            database['embargoterminationapproval'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'embargoed_registration': node._id
                }}
            )

    if database['preprintservice'].find({'node': old_id}).count():
        logger.info('** Updating PreprintServices {}'.format([d['_id'] for d in database['preprintservice'].find({'node': old_id})]))
        for doc in database['preprintservice'].find({'node': old_id}):
            database['preprintservice'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
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
    target_documents = list(get_targets())
    target_ids = [d['_id'] for d in target_documents]
    target_count = len(target_documents)
    successes = []
    failures = []
    created_preprints = []
    external_preprints = []
    preprint_node_mapping = {}

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
                if preprints[preprint_id][1]:
                    external_preprints.append(preprint_id)
            preprint_node_mapping.update(preprints)
            successes.append(node['_id'])
            logger.info('({}-{}/{}) Successfully migrated {}'.format(
                len(successes),
                len(failures),
                target_count, 
                node['_id']
                )
            )

    new_osf_preprints = list(set(created_preprints)-set(target_ids + external_preprints))
    logger.info('OSF Preprints with new _ids (older than {} minutes): {}'.format(
        swap_cutoff.seconds/60,  # timedeltas have .days, .seconds, and .microseonds but not .minutes
        new_osf_preprints))
    logger.info('OSF Preprint-Node map: {}'.format(
        ''.join(['{}-{}, '.format(preprint_id, preprint_node_mapping[preprint_id][0]) for preprint_id in new_osf_preprints])))
    logger.info('External Preprints with new _ids: {}'.format(list(external_preprints)))
    logger.info('External Preprint-Node map: {}'.format(
        ''.join(['{}-{}, '.format(preprint_id, preprint_node_mapping[preprint_id][0]) for preprint_id in external_preprints])))
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
    settings.SHARE_API_TOKEN = None
    with TokuTransaction():
        migrate(swap_cutoff=td)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
