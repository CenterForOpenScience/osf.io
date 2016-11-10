from datetime import timedelta
import json
import logging
import re
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


# Multiple updates to any <node>.child_node_subscriptions causes only the last one to succeed.
# Cache the intended value instead, updating it here before writing.
cns_dict_to_update = {}

# Dictionary containing {<preprint._id>: <node._id>} mapping for pairs that swapped guids
preprint_node_swapped_ids_map = {}


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
            node.reload()
            preprint.reload()
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
            database['preprintservice'].find_and_modify(
                {'_id': preprint._id},
                {'$set': {
                    'date_modified': document['preprint_created'],
                }}
            )
            created.update({preprint._id: (node._id, non_osf_provider)})

    return created

def should_swap_guids(node, preprint, swap_cutoff):
    preprint.reload()
    logger.info('Preprint {} - Node {} timedelta = {}'.format(preprint._id, node._id, preprint.date_created - node.date_created))
    return preprint.date_created - node.date_created < swap_cutoff

def swap_guids(node, preprint):
    logger.info('* Swapping guids for preprint {} and node {}'.format(preprint._id, node._id))
    preprint_node_swapped_ids_map[node._id] = preprint._id  # node._id is about to become preprint._id, reverse here
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

    bns_owner = list(database['boxnodesettings'].find({'owner': old_id}))
    if bns_owner:
        logger.info('** Updating {} BoxNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in bns_owner]))
        for doc in bns_owner:
            database['boxnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    bus_og = list(database['boxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if bus_og:
        logger.info('** Updating {} BoxUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in bus_og]))
        for doc in bus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['boxusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )
    advns_o = list(database['addondataversenodesettings'].find({'owner': old_id}))        
    if advns_o:
        logger.info('** Updating {} AddonDataverseNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in advns_o]))
        for doc in advns_o:
            database['addondataversenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    advus_og = list(database['addondataverseusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if advus_og:
        logger.info('** Updating {} AddonDataverseUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in advus_og]))
        for doc in advus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['addondataverseusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    dbns_o = list(database['dropboxnodesettings'].find({'owner': old_id}))
    if dbns_o:
        logger.info('** Updating {} DropboxNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in dbns_o]))
        for doc in dbns_o:
            database['dropboxnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    dbus_og = list(database['dropboxusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if dbus_og:
        logger.info('** Updating {} DropboxUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in dbus_og]))
        for doc in dbus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['dropboxusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    afsns_o = list(database['addonfigsharenodesettings'].find({'owner': old_id}))
    if afsns_o:
        logger.info('** Updating {} AddonFigShareNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in afsns_o]))
        for doc in afsns_o:
            database['addonfigsharenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ## Figshare has no oauth_grants

    fwns_o = list(database['forwardnodesettings'].find({'owner': old_id}))
    if fwns_o:
        logger.info('** Updating {} ForwardNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in fwns_o]))
        for doc in fwns_o:
            database['forwardnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ghns_o = list(database['githubnodesettings'].find({'owner': old_id}))
    if ghns_o:
        logger.info('** Updating {} GithubNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in ghns_o]))
        for doc in ghns_o:
            database['githubnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ghus_og = list(database['githubusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if ghus_og:
        logger.info('** Updating {} GithubUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in ghus_og]))
        for doc in ghus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['githubusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    gdns_o = list(database['googledrivenodesettings'].find({'owner': old_id}))
    if gdns_o:
        logger.info('** Updating {} GoogleDriveNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in gdns_o]))
        for doc in gdns_o:
            database['googledrivenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    gdus_og = list(database['googledriveusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if gdus_og:
        logger.info('** Updating {} GoogleDriveUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in gdus_og]))
        for doc in gdus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['googledriveusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    mns_o = list(database['mendeleynodesettings'].find({'owner': old_id}))
    if mns_o:
        logger.info('** Updating {} MendeleyNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in mns_o]))
        for doc in mns_o:
            database['mendeleynodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    mus_og = list(database['mendeleyusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if mus_og:
        logger.info('** Updating {} MendeleyUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in mus_og]))
        for doc in mus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['mendeleyusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    osfsns_o = list(database['osfstoragenodesettings'].find({'owner': old_id}))
    if osfsns_o:
        logger.info('** Updating {} OsfStorageNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in osfsns_o]))
        for doc in osfsns_o:
            database['osfstoragenodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ocns_o = list(database['addonowncloudnodesettings'].find({'owner': old_id}))
    if ocns_o:
        logger.info('** Updating {} AddonOwnCloudNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in ocns_o]))
        for doc in ocns_o:
            database['addonowncloudnodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    ocus_og = list(database['addonowncloudusersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if ocus_og:
        logger.info('** Updating {} AddonOwnCloudUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in ocus_og]))
        for doc in ocus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['addonowncloudusersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    s3ns_o = list(database['s3nodesettings'].find({'owner': old_id}))
    if s3ns_o:
        logger.info('** Updating {} s3NodeSettings (owner) {}'.format(old_id, [d['_id'] for d in s3ns_o]))
        for doc in s3ns_o:
            database['s3nodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    s3us_og = list(database['s3usersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if s3us_og:
        logger.info('** Updating {} S3UserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in s3us_og]))
        for doc in s3us_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['s3usersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    awns_o = list(database['addonwikinodesettings'].find({'owner': old_id}))
    if awns_o:
        logger.info('** Updating {} AddonWikiNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in awns_o]))
        for doc in awns_o:
            database['addonwikinodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    nwp_n = list(database['nodewikipage'].find({'node': old_id}))
    if nwp_n:
        logger.info('** Updating {} NodeWikiPage (node) {}'.format(old_id, [d['_id'] for d in nwp_n]))
        for doc in nwp_n:
            database['nodewikipage'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    zns_o = list(database['zoteronodesettings'].find({'owner': old_id}))
    if zns_o:
        logger.info('** Updating {} ZoteroNodeSettings (owner) {}'.format(old_id, [d['_id'] for d in zns_o]))
        for doc in zns_o:
            database['zoteronodesettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'owner': node._id
                }}
            )

    zus_og = list(database['zoterousersettings'].find({'oauth_grants.{}'.format(old_id): {'$ne': None}}))
    if zus_og:
        logger.info('** Updating {} ZoteroUserSettings (oauth_grants) {}'.format(old_id, [d['_id'] for d in zus_og]))
        for doc in zus_og:
            og = doc['oauth_grants']
            og[node._id] = og.pop(old_id)
            database['zoterousersettings'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'oauth_grants': og
                }}
            )

    aj_sn = list(database['archivejob'].find({'src_node': old_id}))
    if aj_sn:
        logger.info('** Updating {} ArchiveJobs (src_node) {}'.format(old_id, [d['_id'] for d in aj_sn]))
        for doc in aj_sn:
            database['archivejob'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'src_node': node._id
                }}
            )

    tfn_n = list(database['trashedfilenode'].find({'node': old_id}))
    if tfn_n:
        logger.info('** Updating {} TrashedFileNodes (node) {}'.format(old_id, [d['_id'] for d in tfn_n]))
        for doc in tfn_n:
            del_on = doc.pop('deleted_on')  # Remove non-JSON-serializable datetime fields
            last_touch = doc.pop('last_touched')  
            hist_mods = [doc['history'][doc['history'].index(h)].pop('modified') for h in doc['history']]
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc)))
            for i, mod in enumerate(hist_mods):
                replacement['history'][i]['modified'] = mod
            database['trashedfilenode'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': replacement['node'],
                    'history': replacement['history']
                }}
            )

    sfn_n = list(database['storedfilenode'].find({'node': old_id}))
    if sfn_n:
        logger.info('** Updating {} StoredFileNodes (node) {}'.format(old_id, [d['_id'] for d in sfn_n]))
        for doc in sfn_n:
            doc.pop('last_touched')  # Remove non-JSON-serializable datetime fields
            hist_mods = [doc['history'][doc['history'].index(h)].pop('modified') for h in doc['history']]
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc)))
            for i, mod in enumerate(hist_mods):
                replacement['history'][i]['modified'] = mod
            database['storedfilenode'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': replacement['node'],
                    'history': replacement['history']
                }}
            )

    com_n = list(database['comment'].find({'node': old_id}))
    if com_n:
        logger.info('** Updating {} Comments (node) {}'.format(old_id, [d['_id'] for d in com_n]))
        for doc in com_n:
            database['comment'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    com_t = list(database['comment'].find({'target': {'$in': [old_id]}}))
    if com_t:
        logger.info('** Updating {} Comments (target) {}'.format(old_id, [d['_id'] for d in com_t]))
        for doc in com_t:
            targ = doc['target']
            targ.insert(targ.index(old_id), node._id)
            targ.remove(old_id)
            database['comment'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'target': targ
                }}
            )

    com_t = list(database['comment'].find({'root_target': {'$in': [old_id]}}))
    if com_t:
        logger.info('** Updating {} Comments (root_target) {}'.format(old_id, [d['_id'] for d in com_t]))
        for doc in com_t:
            rtarg = doc['root_target']
            rtarg.insert(rtarg.index(old_id), node._id)
            rtarg.remove(old_id)
            database['comment'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'root_target': rtarg
                }}
            )

    nl_on = list(database['nodelog'].find({'original_node': old_id}))
    if nl_on:
        logger.info('** Updating {} NodeLogs (original_node) {}'.format(old_id, [d['_id'] for d in nl_on]))
        for doc in nl_on:
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'original_node': node._id
                }}
            )

    nl_n = list(database['nodelog'].find({'node': old_id}))
    if nl_n:
        logger.info('** Updating {} NodeLogs (node) {}'.format(old_id, [d['_id'] for d in nl_n]))
        for doc in nl_n:
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    nl_pac = list(database['nodelog'].find({'params.auth.callback_url': {'$regex': '/{}/'.format(old_id)}}))
    if nl_pac:
        logger.info('** Updating {} NodeLogs (params.auth.callback_url) {}'.format(old_id, [d['_id'] for d in nl_pac]))
        for doc in nl_pac:
            params = doc['params']
            params['auth']['callback_url'] = params['auth']['callback_url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_pn = list(database['nodelog'].find({'params.node': old_id}))
    if nl_pn:
        logger.info('** Updating {} NodeLogs (params.node) {}'.format(old_id, [d['_id'] for d in nl_pn]))
        for doc in nl_pn:
            params = doc['params']
            params['node'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_ppar = list(database['nodelog'].find({'params.parent': old_id}))
    if nl_ppar:
        logger.info('** Updating {} NodeLogs (params.parent) {}'.format(old_id, [d['_id'] for d in nl_ppar]))
        for doc in nl_ppar:
            params = doc['params']
            params['parent'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_ppro = list(database['nodelog'].find({'params.project': old_id}))
    if nl_ppro:
        logger.info('** Updating {} NodeLogs (params.project) {}'.format(old_id, [d['_id'] for d in nl_ppro]))
        for doc in nl_ppro:
            params = doc['params']
            params['project'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_ppn = list(database['nodelog'].find({'params.parent_node': old_id}))
    if nl_ppn:
        logger.info('** Updating {} NodeLogs (params.parent_node) {}'.format(old_id, [d['_id'] for d in nl_ppn]))
        for doc in nl_ppn:
            params = doc['params']
            params['parent_node'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_pdn = list(database['nodelog'].find({'params.destination.nid': old_id}))
    if nl_pdn:
        logger.info('** Updating {} NodeLogs (params.destination.nid) {}'.format(old_id, [d['_id'] for d in nl_pdn]))
        for doc in nl_pdn:
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

    nl_pdr = list(database['nodelog'].find({'params.destination.resource': old_id}))
    if nl_pdr:
        logger.info('** Updating {} NodeLogs (params.destination.resource) {}'.format(old_id, [d['_id'] for d in nl_pdr]))
        for doc in nl_pdr:
            params = doc['params']
            params['destination']['resource'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_pdni = list(database['nodelog'].find({'params.destination.node._id': old_id}))
    if nl_pdni:
        logger.info('** Updating {} NodeLogs (params.destination.node._id) {}'.format(old_id, [d['_id'] for d in nl_pdni]))
        for doc in nl_pdni:
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

    nl_ppi = list(database['nodelog'].find({'params.pointer.id': old_id}))
    if nl_ppi:
        logger.info('** Updating {} NodeLogs (params.pointer.id) {}'.format(old_id, [d['_id'] for d in nl_ppi]))
        for doc in nl_ppi:
            params = doc['params']
            params['pointer']['id'] = node._id
            if params['pointer'].get('url', None):
                params['pointer']['url'] = params['pointer']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_psn = list(database['nodelog'].find({'params.source.nid': old_id}))
    if nl_psn:
        logger.info('** Updating {} NodeLogs (params.source.nid) {}'.format(old_id, [d['_id'] for d in nl_psn]))
        for doc in nl_psn:
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

    nl_psni = list(database['nodelog'].find({'params.source.node._id': old_id}))
    if nl_psni:
        logger.info('** Updating {} NodeLogs (params.source.node._id) {}'.format(old_id, [d['_id'] for d in nl_psni]))
        for doc in nl_psni:
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

    nl_psr = list(database['nodelog'].find({'params.source.resource': old_id}))
    if nl_psr:
        logger.info('** Updating {} NodeLogs (params.source.resource) {}'.format(old_id, [d['_id'] for d in nl_psr]))
        for doc in nl_psr:
            params = doc['params']
            params['source']['resource'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_ptni = list(database['nodelog'].find({'params.template_node._id': old_id}))
    if nl_ptni:
        logger.info('** Updating {} NodeLogs (params.template_node._id) {}'.format(old_id, [d['_id'] for d in nl_ptni]))
        for doc in nl_ptni:
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

    nl_pud = list(database['nodelog'].find({'params.urls.download': {'$regex': '/{}/'.format(old_id)}}))
    if nl_pud:
        logger.info('** Updating {} NodeLogs (params.source.node._id) {}'.format(old_id, [d['_id'] for d in nl_pud]))
        for doc in nl_pud:
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

    ptr_n = list(database['pointer'].find({'node': old_id}))
    if ptr_n:
        logger.info('** Updating {} Pointers (node) {}'.format(old_id, [d['_id'] for d in ptr_n]))
        for doc in ptr_n:
            database['pointer'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    n_ff = list(database['node'].find({'forked_from': old_id}))
    if n_ff:
        logger.info('** Updating {} Nodes (forked_from) {}'.format(old_id, [d['_id'] for d in n_ff]))
        for doc in n_ff:
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'forked_from': node._id
                }}
            )

    n_rf = list(database['node'].find({'registered_from': old_id}))
    if n_rf:
        logger.info('** Updating {} Nodes (registered_from) {}'.format(old_id, [d['_id'] for d in n_rf]))
        for doc in n_rf:
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'registered_from': node._id
                }}
            )

    n_root = list(database['node'].find({'root': old_id}))
    if n_root:
        logger.info('** Updating {} Nodes (root) {}'.format(old_id, [d['_id'] for d in n_root]))
        for doc in n_root:
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'root': node._id
                }}
            )

    n_par = list(database['node'].find({'parent': old_id}))
    if n_par:
        logger.info('** Updating {} Nodes (parent) {}'.format(old_id, [d['_id'] for d in n_par]))
        for doc in n_par:
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'parent': node._id
                }}
            )

    n_cns = list(database['node'].find({'$where': 'if (this.child_node_subscriptions!==undefined){{var keys=Object.keys(this.child_node_subscriptions);for(var i=0;i<keys.length;i+=1){{if(this.child_node_subscriptions[keys[i]].indexOf("{}")!==-1){{return true}}}}}}return false;'.format(old_id)}))
    if n_cns:
        docs = list(n_cns)
        logger.info('** Updating {} Nodes (child_node_subscriptions) {}'.format(old_id, [d['_id'] for d in docs]))
        for doc in docs:
            if doc['_id'] in cns_dict_to_update:
                cns = cns_dict_to_update[doc['_id']]
            else:
                cns = doc['child_node_subscriptions']
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(cns)))
            cns_dict_to_update[doc['_id']] = replacement
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'child_node_subscriptions': replacement
                }}
            )

    nd_nl = list(database['notificationdigest'].find({'node_lineage': {'$in': [old_id]}}))
    if nd_nl:
        logger.info('** Updating {} NotificationDigest (node_lineage) {}'.format(old_id, [d['_id'] for d in nd_nl]))
        for doc in nd_nl:
            nl = doc['node_lineage']
            nl.insert(nl.index(old_id), node._id)
            nl.remove(old_id)
            if doc['message'].find('/{}/'.format(old_id)) != -1:  # avoid html regexes
                message = doc['message'].replace('/{}/'.format(old_id), '/{}/'.format(node._id))
                database['notificationdigest'].find_and_modify(
                    {'_id': doc['_id']},
                    {'$set':{
                        'message': message,
                        'node_lineage': nl
                    }}
                )
            else:
                database['notificationdigest'].find_and_modify(
                    {'_id': doc['_id']},
                    {'$set':{
                        'node_lineage': nl
                    }}
                )

    ns_i = list(database['notificationsubscription'].find({'_id': {'$regex': old_id}}))
    if ns_i:
        logger.info('** Updating {} NotificationSubscription (_id, owner) {}'.format(old_id, [d['_id'] for d in ns_i]))
        for doc in ns_i:
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc)))
            new_id = replacement.pop('_id')
            database['notificationsubscription'].find_and_modify(
                {'_id': new_id},
                {'$set':replacement},
                upsert=True
            )
            database['notificationsubscription'].remove({'_id': doc['_id']})

    u_uc = list(database['user'].find({'unclaimed_records.{}'.format(old_id): {'$ne': None}}))
    if u_uc:
        logger.info('** Updating {} Users (unclaimed_records) {}'.format(old_id, [d['_id'] for d in u_uc]))
        for doc in u_uc:
            ucr = doc['unclaimed_records']
            ucr[node._id] = ucr.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'unclaimed_records': ucr
                }}
            )

    u_caer = list(database['user'].find({'contributor_added_email_records.{}'.format(old_id): {'$ne': None}}))
    if u_caer:
        logger.info('** Updating {} Users (contributor_added_email_records) {}'.format(old_id, [d['_id'] for d in u_caer]))
        for doc in u_caer:
            caer = doc['contributor_added_email_records']
            caer[node._id] = caer.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'contributor_added_email_records': caer
                }}
            )

    u_nc = list(database['user'].find({'notifications_configured.{}'.format(old_id): {'$ne': None}}))
    if u_nc:
        logger.info('** Updating {} Users (notifications_configured) {}'.format(old_id, [d['_id'] for d in u_nc]))
        for doc in u_nc:
            nc = doc['notifications_configured']
            nc[node._id] = nc.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'notifications_configured': nc
                }}
            )

    u_cvt = list(database['user'].find({'comments_viewed_timestamp.{}'.format(old_id): {'$ne': None}}))
    if u_cvt:
        logger.info('** Updating {} Users (comments_viewed_timestamp) {}'.format(old_id, [d['_id'] for d in u_cvt]))
        for doc in u_cvt:
            nc = doc['comments_viewed_timestamp']
            nc[node._id] = nc.pop(old_id)
            database['user'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'comments_viewed_timestamp': nc
                }}
            )

    pc_i = list(database['pagecounters'].find({'_id': {'$regex': ':{}:'.format(old_id)}}))
    if pc_i:
        logger.info('** Updating {} PageCounters (_id) {}'.format(old_id, [d['_id'] for d in pc_i]))
        for doc in pc_i:
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc)))
            new_id = replacement.pop('_id')
            database['pagecounters'].find_and_modify(
                {'_id': new_id},
                {'$set':replacement},
                upsert=True
            )
            database['pagecounters'].remove({'_id': doc['_id']})

    ss_dv = list(database['session'].find({'data.visited': {'$regex': ':{}:'.format(old_id)}}))
    if ss_dv:
        logger.info('** Updating {} Session (data) {}'.format(old_id, [d['_id'] for d in ss_dv]))
        for doc in ss_dv:
            repl_data = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc['data'])))
            database['session'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'data': repl_data
                }}
            )

    wc_n = list(database['watchconfig'].find({'node': old_id}))
    if wc_n:
        logger.info('** Updating {} WatchConfigs (node) {}'.format(old_id, [d['_id'] for d in wc_n]))
        for doc in wc_n:
            database['watchconfig'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'node': node._id
                }}
            )

    pl_n = list(database['privatelink'].find({'nodes': old_id}))
    if pl_n:
        logger.info('** Updating {} PrivateLinks (nodes) {}'.format(old_id, [d['_id'] for d in pl_n]))
        for d in pl_n:
            new_nodes = d['nodes']
            new_nodes.remove(old_id)
            new_nodes.append(node._id) 
            database['privatelink'].find_and_modify(
                {'_id': d['_id']},
                {'$set':{
                    'nodes': new_nodes
                }}
            )

    dr_bf = list(database['draftregistration'].find({'branched_from': old_id}))
    if dr_bf:
        logger.info('** Updating {} DraftRegistrations (branched_from) {}'.format(old_id, [d['_id'] for d in dr_bf]))
        for doc in dr_bf:
            database['draftregistration'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'branched_from': node._id
                }}
            )

    dr_rn = list(database['draftregistration'].find({'registered_node': old_id}))
    if dr_rn:
        logger.info('** Updating {} DraftRegistrations (registered_node) {}'.format(old_id, [d['_id'] for d in dr_rn]))
        for doc in dr_rn:
            database['draftregistration'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'registered_node': node._id
                }}
            )

    eta_er = list(database['embargoterminationapproval'].find({'embargoed_registration': old_id}))
    if eta_er:
        logger.info('** Updating {} EmbargoTerminationApprovals (embargoed_registration) {}'.format(old_id, [d['_id'] for d in eta_er]))
        for doc in eta_er:
            database['embargoterminationapproval'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'embargoed_registration': node._id
                }}
            )

    ra_su = list(database['registrationapproval'].find({'$where': 'var keys=Object.keys(this.stashed_urls);for(var i=0;i<keys.length;i+=1){{if(this.stashed_urls[keys[i]].view.indexOf("{}")!==-1){{return true}}if(this.stashed_urls[keys[i]].approve.indexOf("{}")!==-1){{return true}}if(this.stashed_urls[keys[i]].reject.indexOf("{}")!==-1){{return true}}}}return false;'.format(old_id, old_id, old_id)}))
    if ra_su:
        logger.info('** Updating {} RegistrationApprovals (stashed_urls) {}'.format(old_id, [d['_id'] for d in ra_su]))
        for doc in ra_su:
            updated_stash = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc['stashed_urls'])))
            database['registrationapproval'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'stashed_urls': updated_stash
                }}
            )

    idf_r = list(database['identifier'].find({'referent': old_id}))
    if idf_r:
        logger.info('** Updating {} Identifiers (referent) {}'.format(old_id, [d['_id'] for d in idf_r]))
        for doc in idf_r:
            ref = doc['referent']
            ref[1] = 'preprintservice'
            database['identifier'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'referent': ref
                }}
            )

    qm_dn = list(database['queuedmail'].find({'data.nid': old_id}))
    if qm_dn:
        logger.info('** Updating {} QueuedMails (data.nid) {}'.format(old_id, [d['_id'] for d in qm_dn]))
        for doc in qm_dn:
            repl_data = json.loads(re.sub(r'\b{}\b'.format(old_id), node._id, json.dumps(doc['data'])))
            database['queuedmail'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'data': repl_data
                }}
            )

    ps_n = list(database['preprintservice'].find({'node': old_id}))
    if ps_n:
        logger.info('** Updating {} PreprintServices (node) {}'.format(old_id, [d['_id'] for d in ps_n]))
        for doc in ps_n:
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
    logger.info('Swapped Preprint-Node map: {}'.format(
        ''.join(['{}-{}, '.format(preprint_id, preprint_node_swapped_ids_map[preprint_id]) for preprint_id in preprint_node_swapped_ids_map])))
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
