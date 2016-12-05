from datetime import timedelta
import json
import logging
import re
import sys

from modularodm import Q
from modularodm.storage.base import KeyExistsException
from modularodm.exceptions import NoResultsFound

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website import models 
from website import settings

logger = logging.getLogger(__name__)


# Target set. Loaded from --targets flag
target_data = []

POSSIBLE_PREPRINT_PROVIDER_KEYS = None 
SOC_SUBJ_ID = None
ENG_SUBJ_ID = None
PSY_SUBJ_ID = None

def set_globals():
    # Must be run after backends are set with init_app
    global POSSIBLE_PREPRINT_PROVIDER_KEYS
    global SOC_SUBJ_ID
    global ENG_SUBJ_ID
    global PSY_SUBJ_ID

    POSSIBLE_PREPRINT_PROVIDER_KEYS = set([t._id for t in models.Tag.find(Q('lower', 'in', ['psyarxiv','engrxiv','socarxiv']))])

    try:
        # PLOS
        SOC_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Social and behavioral sciences'))._id
        ENG_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Engineering and technology'))._id
        PSY_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Social psychology'))._id
    except NoResultsFound:
        try:
            # BePress
            SOC_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Social and Behavioral Sciences'))._id  
            ENG_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Engineering'))._id
            PSY_SUBJ_ID = models.Subject.find_one(Q('text', 'eq', 'Social Psychology'))._id
        except:
            raise RuntimeError('Unable to find default subjects. Please ensure the existence of:\n\t' + \
                '\'Engineering and technology\' (BePress: \'Engineering\'),\n\t' + \
                '\'Social and behavioral sciences\' (BePress: \'Social and Behavioral Sciences\'),\n\t' + \
                '\'Social psychology\' (BePress: \'Social Psychology\')'
            )

# Multiple updates to any <node>.child_node_subscriptions causes only the last one to succeed.
# Cache the intended value instead, updating it here before writing.
cns_dict_to_update = {}

# Dictionary containing {<preprint._id>: <node._id>} mapping for pairs that swapped guids
preprint_node_swapped_ids_map = {}

successes = []
failures = []
created_preprints = []
external_preprints = []
preprint_node_mapping = {}

def create_indices():
    logger.info('Creating database indices...')
    database.nodelog.ensure_index([('params.auth.callback_url', 1)])
    database.nodelog.ensure_index([('params.node', 1)])
    database.nodelog.ensure_index([('params.parent', 1)])
    database.nodelog.ensure_index([('params.project', 1)])
    database.nodelog.ensure_index([('params.parent_node', 1)])
    database.nodelog.ensure_index([('params.destination.nid', 1)])
    database.nodelog.ensure_index([('params.destination.resource', 1)])
    database.nodelog.ensure_index([('params.destination.node._id', 1)])
    database.nodelog.ensure_index([('params.pointer.id', 1)])
    database.nodelog.ensure_index([('params.source.nid', 1)])
    database.nodelog.ensure_index([('params.source.node._id', 1)])
    database.nodelog.ensure_index([('params.source.resource', 1)])
    database.nodelog.ensure_index([('params.template_node.id', 1)])
    database.nodelog.ensure_index([('params.registration', 1)])
    database.nodelog.ensure_index([('params.fork', 1)])
    database.nodelog.ensure_index([('params.source.node._id', 1)])
    database.nodewikipage.ensure_index([('node', 1)])
    database.identifier.ensure_index([('referent', 1)])
    database.session.ensure_index([('data', 1)])

def drop_indices():
    logger.info('Cleaning up indices...')
    database.nodelog.drop_index([('params.auth.callback_url', 1)])
    database.nodelog.drop_index([('params.node', 1)])
    database.nodelog.drop_index([('params.parent', 1)])
    database.nodelog.drop_index([('params.project', 1)])
    database.nodelog.drop_index([('params.parent_node', 1)])
    database.nodelog.drop_index([('params.destination.nid', 1)])
    database.nodelog.drop_index([('params.destination.resource', 1)])
    database.nodelog.drop_index([('params.destination.node._id', 1)])
    database.nodelog.drop_index([('params.pointer.id', 1)])
    database.nodelog.drop_index([('params.source.nid', 1)])
    database.nodelog.drop_index([('params.source.node._id', 1)])
    database.nodelog.drop_index([('params.source.resource', 1)])
    database.nodelog.drop_index([('params.template_node.id', 1)])
    database.nodelog.drop_index([('params.registration', 1)])
    database.nodelog.drop_index([('params.fork', 1)])
    database.nodelog.drop_index([('params.source.node._id', 1)])
    database.nodewikipage.drop_index([('node', 1)])
    database.identifier.drop_index([('referent', 1)])
    database.session.drop_index([('data', 1)])

def validate_target(target):
    logger.info('* Validating and updating node {}'.format(target['node_id']))
    updates = {}
    node = database['node'].find_one(target['node_id'])
    file = database['storedfilenode'].find_one(target['file_id'])

    assert node, 'Unable to find Node with _id {}'.format(target['node_id'])
    assert file, 'Unable to find File with _id {}'.format(target['file_id'])
    assert target['provider_id'] in set([tag.lower() for tag in node.get('tags', [])]) & POSSIBLE_PREPRINT_PROVIDER_KEYS, 'Unable to infer PreprintProvider for node {} with tags {}'.format(node['_id'], node['tags'])
    assert file['node'] == node['_id'], 'File {} with `node` {} not attached to Node {}'.format(file_id, file['node'], node['_id'])
    assert not database['preprintservice'].find({'node': target['node_id']}, {'_id': 1}).count(), 'Cannot migrate a node that already has a preprint'

    if target.get('subjects'):
        validate_subjects(target['subjects'])

    if not node.get('preprint_file', None):
        updates.update({'preprint_file': file['_id']})
    if not node.get('preprint_created', None):
        updates.update({'preprint_created': infer_preprint_created(target['node_id'], target['provider_id'])})

    if updates:
        logger.debug('{} has no preprint_file, setting'.format(node['_id']))
        database['node'].find_and_modify(
            {'_id': node['_id']},
            {'$set': updates}
        )

def validate_subjects(subj_hierarchy):
    for subject_list in subj_hierarchy:
        for subject_id in subject_list:
            subject = models.Subject.load(subject_id)
            if not subject:
                logger.error('Found nonexistant subject {}.'.format(subject_id))
                raise Exception('Found nonexistant subject {}.'.format(subject_id)) 
            if subject.parents and not set([c._id for c in subject.parents]) & set(subject_list):
                logger.error('Found subject {} without parents.'.format(subject_id))
                raise Exception('Found subject {} without parents.'.format(subject_id))

def infer_preprint_created(node_id, provider_id):
    logs = models.NodeLog.find(Q('node', 'eq', node_id) & Q('action', 'eq', 'tag_added') & Q('params.tag', 'in', list(POSSIBLE_PREPRINT_PROVIDER_KEYS)))
    return min([l.date for l in logs if re.match(provider_id, l.params['tag'], re.I)])

def add_preprint_log(preprint):
    logs = models.NodeLog.find(Q('node', 'eq', preprint.node._id) & Q('action', 'eq', 'tag_added') & Q('params.tag', 'in', [preprint.provider._id]))
    date_preprint_created = min([l.date for l in logs])
    user = logs[0].user
    new_log = models.NodeLog(
        action='preprint_initiated',
        user=user,
        params={
            'node': preprint.node._id,
            'preprint': preprint._id
        },
        node=preprint.node._id,
        original_node=preprint.node._id,
        date=date_preprint_created,
    )
    new_log.save()

def create_preprint_service_from_target(target, swap_cutoff):
    created = {}
    node_doc = database['node'].find_one(target['node_id'])
    provider_id = target['provider_id']
    non_osf_provider = provider_id != 'osf'
    node = models.Node.load(node_doc['_id'])
    provider = models.PreprintProvider.load(provider_id)
    # primary_file already set correctly* on node
    if not provider:
        raise Exception('Unable to find provider {} for node {}, erroring'.format(provider_id, node_doc['_id']))
    if not node:
        raise Exception('Unable to find node {}, erroring.'.format(node_doc['_id'])) 

    subjects = target.get('subjects', {'socarxiv': [[SOC_SUBJ_ID]], 'engrxiv': [[ENG_SUBJ_ID]], 'psyarxiv': [[SOC_SUBJ_ID, PSY_SUBJ_ID]]}[provider_id])

    try:
        logger.info('* Creating preprint for node {}'.format(node._id))
        preprint = models.PreprintService(node=node, provider=provider)
        preprint.save()
        database['preprintservice'].find_and_modify(
            {'_id': preprint._id},
            {'$set': {
                'date_created': node_doc['preprint_created'],
                'date_published': node_doc['preprint_created'],
                'subjects': subjects,
                'is_published': True
            }}
        )
    except KeyExistsException:
        logger.warn('Duplicate PreprintService found for provider {} on node {}, skipping'.format(provider._id, node._id))
    else:
        if node_doc.get('preprint_doi'):
            database['node'].find_and_modify(
                {'_id': node._id},
                {'$set': {
                    'preprint_article_doi': node_doc['preprint_doi']
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
        if should_swap_guids(node, preprint, swap_cutoff):
            swap_guids(node, preprint)
        node.reload()
        preprint.reload()
        preprint.node.reload()
        # add_preprint_log(preprint)  # Don't log this action
        database['preprintservice'].find_and_modify(
            {'_id': preprint._id},
            {'$set': {
                'date_modified': node_doc['preprint_created'],
            }}
        )
        created.update({preprint._id: (node._id, non_osf_provider)})
    node.system_tags.append('migrated_from_osf4m')

    if not node.description:
        wiki_home = node.get_wiki_page('home')
        if wiki_home and wiki_home.content:
            node.description = wiki_home.content
    node.save()

    return created

def should_swap_guids(node, preprint, swap_cutoff):
    logger.info('Preprint {} - Node {} timedelta = {}'.format(preprint._id, node._id, preprint.date_created - node.date_created))
    not_too_old = preprint.date_created - node.date_created < swap_cutoff
    not_previously_swapped = not database['preprintservice'].find({'node': node._id}).count() > 1
    if not_too_old and not_previously_swapped:
        return True
    if not not_too_old:
        logger.info('* Not swapping guids for preprint {} and preexisting node {}'.format(preprint._id, node._id))
    if not not_previously_swapped:
        logger.info('* Not swapping guids for preprint {} and already-swapped node {}'.format(preprint._id, node._id))
    return False

def swap_guids(node, preprint):
    if node._backrefs.get('addons', {}).get('addonfilesnodesettings'):
        database['node'].find_and_modify(
            {'_id': node._id},
            {'$unset': {
                '__backrefs.addons.addonfilesnodesettings': ''
            }}
        )
        node.reload()
    if node._backrefs.get('uploads', {}).get('nodefile'):
        database['node'].find_and_modify(
            {'_id': node._id},
            {'$unset': {
                '__backrefs.uploads.nodefile': ''
            }}
        )
        node.reload()
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

    nl_ptni = list(database['nodelog'].find({'params.template_node.id': old_id}))
    if nl_ptni:
        logger.info('** Updating {} NodeLogs (params.template_node.id) {}'.format(old_id, [d['_id'] for d in nl_ptni]))
        for doc in nl_ptni:
            params = doc['params']
            params['template_node']['id'] = node._id
            if params['template_node'].get('url', None):
                params['template_node']['url'] = params['template_node']['url'].replace('{}/'.format(old_id), '{}/'.format(node._id))
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_pr = list(database['nodelog'].find({'params.registration': old_id}))
    if nl_pr:
        logger.info('** Updating {} NodeLogs (params.registration) {}'.format(old_id, [d['_id'] for d in nl_pr]))
        for doc in nl_pr:
            params = doc['params']
            params['registration'] = node._id
            database['nodelog'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'params': params
                }}
            )

    nl_pf = list(database['nodelog'].find({'params.fork': old_id}))
    if nl_pf:
        logger.info('** Updating {} NodeLogs (params.fork) {}'.format(old_id, [d['_id'] for d in nl_pf]))
        for doc in nl_pf:
            params = doc['params']
            params['fork'] = node._id
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

    n_tn = list(database['node'].find({'template_node': old_id}))
    if n_tn:
        logger.info('** Updating {} Nodes (template_node) {}'.format(old_id, [d['_id'] for d in n_tn]))
        for doc in n_tn:
            database['node'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'template_node': node._id
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

    mr_r = list(database['mailrecord'].find({'records': [old_id, 'node']}))
    if mr_r:
        logger.info('** Updating {} MailRecords (records) {}'.format(old_id, [d['_id'] for d in mr_r]))
        for doc in mr_r:
            records = doc['records']
            records[records.index([old_id, 'node'])][0] = node._id
            database['mailrecord'].find_and_modify(
                {'_id': doc['_id']},
                {'$set':{
                    'records': records
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

def migrate_target(target, swap_cutoff, target_count):
    validate_target(target)
    preprints = create_preprint_service_from_target(target, swap_cutoff)
    if not preprints:
        failures.append(target['node_id'])
        logger.error('({}-{}/{}) Failed to create any PreprintServices for node {}'.format(
            len(successes),
            len(failures),
            target_count,
            target['node_id'])
        )
    else:
        for preprint_id in preprints:
            created_preprints.append(preprint_id)
            if preprints[preprint_id][1]:
                external_preprints.append(preprint_id)
        preprint_node_mapping.update(preprints)
        successes.append(target['node_id'])
        logger.info('({}-{}/{}) Successfully migrated {}'.format(
            len(successes),
            len(failures),
            target_count,
            target['node_id']
            )
        )

def migrate(swap_cutoff):
    dry_run = '--dry' in sys.argv

    target_data = parse_input()
    target_ids = [d['node_id'] for d in target_data]
    target_count = len(target_data)

    def log_results():
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

    logger.info('Preparing to migrate {} preprint nodes.'.format(target_count))
    logger.info('Cutoff delta for swapping guids is {} seconds'.format(swap_cutoff.total_seconds()))
    for target in target_data:
        try:
            if not dry_run:
                with TokuTransaction():
                    migrate_target(target, swap_cutoff, target_count)
            else:
                migrate_target(target, swap_cutoff, target_count)
        except Exception as e:
            if not isinstance(e, RuntimeError):
                logger.error('MIGRATION FAILED: {}'.format(target))
            log_results()
            raise
    
    log_results()

def parse_input():
    logger.info('Acquiring targets...')
    if '--targets' not in sys.argv and '--auto' not in sys.argv:
        raise RuntimeError('Must either request `--auto` for target selection or manually specify input set with `--targets`.\n\nThis is expected to be a JSON-formatted list of sets of `node_id`, `file_id` and `provider_id`, e.g.\
            \'{"data": [{"node_id": "asdfg", "file_id": "notarealfileid", "provider_id": "notarealproviderid"}]}\'')
    if '--targets' in sys.argv and '--auto' in sys.argv:
        raise RuntimeError('May not automatically get targets and receive specified targets.')
    if '--auto' in sys.argv:
        count = None
        try:
            count = int(sys.argv[1 + sys.argv.index('--auto')])
        except (IndexError, ValueError):
            pass
        targets = [
            {
                'file_id': database['storedfilenode'].find({'node': n._id, 'is_file': True, 'provider': 'osfstorage'}, {'_id': 1})[0]['_id'],
                'node_id': n._id,
                'provider_id': list(set([t.lower for t in n.tags]) & set(['socarxiv', 'engrxiv', 'psyarxiv']))[0]
            } for n in models.Node.find(Q('tags', 'in', list(POSSIBLE_PREPRINT_PROVIDER_KEYS)) & Q('system_tags', 'ne', 'migrated_from_osf4m') & Q('is_deleted', 'ne', True))
            if database['storedfilenode'].find({'node': n._id, 'is_file': True, 'provider': 'osfstorage'}).count() == 1
            and len(list(set([t.lower for t in n.tags]) & set(['socarxiv', 'engrxiv', 'psyarxiv']))) == 1
            and not database['preprintservice'].find({'node': n._id}, {'_id': 1}).count()
        ]
        if count and count < len(targets):
            return targets[:count]
        return targets
    input_string = sys.argv[1 + sys.argv.index('--targets')]
    return json.loads(input_string)['data']

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
    settings.SHARE_URL = None
    set_globals()
    assert all([ENG_SUBJ_ID, SOC_SUBJ_ID, PSY_SUBJ_ID]), 'Default subjects not set.'
    if '--no-addindex' not in sys.argv:
        create_indices()
    if dry_run:
        with TokuTransaction():
            migrate(swap_cutoff=td)
            raise RuntimeError('Dry run, transaction rolled back.')
    else:
        migrate(swap_cutoff=td)
    if '--no-dropindex' not in sys.argv:
        drop_indices()

if __name__ == "__main__":
    main()
