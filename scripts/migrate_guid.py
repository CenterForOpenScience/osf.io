"""
Create a GUID for all non-GUID database records. If record already has a GUID,
skip; if record has an ID but not a GUID, create a GUID matching the ID. Newly
created records will have optimistically generated GUIDs.
"""

import time
import collections

from framework.mongo import StoredObject

from website import models
from website.app import init_app

app = init_app('website.settings', set_backends=True, routes=True)

def count_values(values):
    counts = collections.defaultdict(int)
    for value in values:
        counts[value] += 1
    return counts

def check_conflicts(conflict_models):

    ids = []

    for model in conflict_models:
        ids += list(model.find().__iter__(raw=True))

    if len(set(ids)) != len(ids):
        print(
            'Conflict among models {}'.format(
                ', '.join([model._name for model in conflict_models])
            )
        )

    counts = count_values(ids)
    case_conflicts = [
        _id
        for _id in counts
        if counts[_id] > 1
    ]

    ids = [
        _id.lower()
        for _id in ids
        if _id
    ]

    counts = count_values(ids)
    no_case_conflicts = [
        _id
        for _id in counts
        if counts[_id] > 1
    ]

    return case_conflicts, no_case_conflicts


guid_models = [models.Node, models.User, models.NodeFile,
               models.NodeWikiPage, models.MetaData]

def migrate_guid(conflict_models):
    """Check GUID models for conflicts, then migrate records that are not in
    conflict. Lower-case primary keys; ensure GUIDs for each record; delete
    outdated GUIDs.

    """
    case_conflicts, no_case_conflicts = check_conflicts(conflict_models)

    print 'Case conflicts', case_conflicts
    print 'No-case conflicts', no_case_conflicts

    if case_conflicts:
        raise Exception('Unavoidable conflicts')

    for model in conflict_models:

        print 'Working on model', model._name

        for obj in model.find():

            if obj is None:
                continue

            # Check for existing GUID
            guid = models.Guid.load(obj._primary_key)

            print obj._primary_key

            if guid is not None:

                # Skip if GUID is already lower-cased
                if guid._primary_key == guid._primary_key.lower():
                    continue

                # Skip if GUID in no-case conflicts
                if guid._primary_key.lower() in no_case_conflicts:
                    continue

                # Delete GUID record
                guid.remove_one(guid)

            # Lower-case if not in no-case conflicts
            if obj._primary_key.lower() not in no_case_conflicts:
                obj._primary_key = obj._primary_key.lower()
                obj.save()

            # Update GUID
            obj._ensure_guid()

            check_pk_change(obj)


def check_pk_change(obj):

    for backref in obj._backrefs_flat:
        pk = backref[1]
        if backref[0][1] == 'guid':
            continue
        Schema = StoredObject.get_collection(backref[0][1])
        record = Schema.load(pk)
        if record is None:
            print 'Error: Backref {} not found'.format(pk)
        field = getattr(record, backref[0][2])
        if isinstance(field, list):
            if obj not in field:
                print 'Error: Object {} not in backref list'.format(pk)
        else:
            if field != obj:
                print 'Error: Object {} not equal to backref'.format(pk)

    for fname, fobj in obj._fields.items():
        if fobj._is_foreign:
            if fobj._list:
                key = fobj._field_instance._backref_field_name
            else:
                key = fobj._backref_field_name
            if not key:
                continue
            backref_key = '__'.join([
                obj._name,
                key,
                fname,
                ])
            value = getattr(obj, fname)
            if not value:
                continue
            if fobj._list:
                for item in value:
                    if item is None:
                        continue
                    if obj not in getattr(item, backref_key):
                        print 'Error: Obj {} not in backrefs of referent {}'.format(
                            obj._primary_key, fname
                        )
            else:
                if obj not in getattr(value, backref_key):
                    print 'Error: Obj {} not in backrefs of referent {}'.format(
                        obj._primary_key, fname
                    )


def migrate_guid_log(log):
    """Migrate non-reference fields containing primary keys on logs.

    """
    for key in ['project', 'node']:
        if key in log.params:
            value = log.params[key] or ''
            record = models.Node.load(value.lower())
            if record is not None:
                log.params[key] = record._primary_key

    if 'contributor' in log.params:
        if isinstance(log.params['contributor'], basestring):
            record = models.User.load(log.params['contributor'].lower())
            if record:
                log.params['contributor'] = record._primary_key

    if 'contributors' in log.params:
        for idx, uid in enumerate(log.params['contributors']):
            if isinstance(uid, basestring):
                record = models.User.load(uid.lower())
                if record:
                    log.params['contributors'][idx] = record._primary_key

    # Shouldn't have to do this, but some logs users weren't correctly
    # migrated; may have to do with inconsistent backrefs
    data = log.to_storage()
    if data['user']:
        record = models.User.load(data['user'].lower())
        if record:
            log.user = record

    log.save()


def migrate_guid_node(node):
    """Migrate non-reference fields containing primary keys on nodes.

    """

    for idx, contributor in enumerate(node.contributor_list):
        if 'id' in contributor:
            record = models.User.load(contributor['id'].lower())
            if record:
                node.contributor_list[idx]['id'] = record._primary_key

    for idx, fork in enumerate(node.node__forked):
        if isinstance(fork, basestring):
            record = models.Node.load(fork.lower())
            if record:
                node.node__forked[idx] = record._primary_key

    for idx, registration in enumerate(node.node__registrations):
        if isinstance(registration, basestring):
            record = models.Node.load(registration.lower())
            if record:
                node.node__registrations[idx] = record._primary_key

    for page in node.wiki_pages_current:
        record = models.NodeWikiPage.load(str(node.wiki_pages_current[page]).lower())
        if record:
            node.wiki_pages_current[page] = record._primary_key
    for page in node.wiki_pages_versions:
        for idx, wid in enumerate(node.wiki_pages_versions[page]):
            record = models.NodeWikiPage.load(str(wid).lower())
            if record:
                node.wiki_pages_versions[page][idx] = record._primary_key

    for fname in node.files_current:
        record = models.NodeFile.load(str(node.files_current[fname]).lower())
        if record:
            node.files_current[fname] = record._primary_key
    for fname in node.files_versions:
        for idx, fid in enumerate(node.files_versions[fname]):
            record = models.NodeFile.load(str(fid).lower())
            if record:
                node.files_versions[fname][idx] = record._primary_key

    node.save()


def migrate_guid_wiki(wiki):
    """Migrate non-reference fields containing primary keys on wiki pages.

    """

    data = wiki.to_storage()

    uid = data.get('user')
    if uid:
        record = models.User.load(uid.lower())
        if record:
            wiki.user = record

    pid = data.get('node')
    if pid:
        record = models.Node.load(pid.lower())
        if record:
            wiki.node = record

    wiki.save()


if __name__ == '__main__':

    t0 = time.time()

    # Lower-case PKs and ensure GUIDs
    migrate_guid(guid_models)

    # Manual migrations
    for node in models.Node.find():
        #print 'Migrating node', node._primary_key
        migrate_guid_node(node)

    for log in models.NodeLog.find():
        #print 'Migrating log', log._primary_key
        migrate_guid_log(log)

    for wiki in models.NodeWikiPage.find():
        #print 'Migrating wiki', wiki._primary_key
        migrate_guid_wiki(wiki)

    print 'Took {}'.format(time.time() - t0)
