from __future__ import print_function
from __future__ import unicode_literals

import functools
import gc
import operator
import sys
from datetime import datetime

import pytz
from django.db import transaction
from osf_models.models import Collection, Registration
from osf_models.models import Conference
from osf_models.models import Institution
from osf_models.models import MetaSchema
from osf_models.models import Registration
from osf_models.models.base import ObjectIDMixin, GuidMixin

from framework.auth import User as MODMUser
from modularodm import Q as MQ
from osf_models.models import Contributor, Node, Tag, OSFUser
from osf_models.models.sanctions import Embargo, Retraction
from website.models import Embargo as MODMEmbargo
from website.models import Retraction as MODMRetraction
from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from website.project.model import Pointer


class DryMigrationException(BaseException):
    pass


fk_node_fields = [
    'forked_from', 'registered_from', 'root', 'parent_node', 'template_node',
    '_primary_institution', 'embargo'
]
m2m_node_fields = ['nodes', '_affiliated_institutions']
fk_user_fields = ['registered_user', 'creator', 'merged_by', 'initiated_by']
fk_retraction_fields = ['retraction', ]
fk_embargo_fields = ['embargo', ]
m2m_user_fields = [
    'permissions',
    'recently_added',
    'users_watching_node',
    'contributors',
]
m2m_tag_fields = ['tags', 'system_tags']

institution_key_blacklist = fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields + fk_retraction_fields

node_key_blacklist = [
    '__backrefs',
    '_version',
    'expanded',
    # collections
    'is_collection',
    'is_bookmark_collection',
    # registrations
    'is_registration',
    'registered_date',
    'registered_user',
    'registered_schema',
    'registered_meta',
    'registration_approval',
    'retraction',
    'embargo',
    'registered_from',
    # foreign keys not yet implemented
    'logs',
    'is_collection',
    'primary_institution',
    #  '_primary_institution',
    'institution_email_domains',
    'institution_domains',
    'registration_approval',
    'alternative_citations',
    'registered_schema',
    'affiliated_institutions',
    #  '_affiliated_institutions',
     'institution_banner_name',
     'institution_id',
     'institution_auth_url',
     'institution_logo_name',
    'contributors',  # done elsewhere
    # 'retraction',
    # 'embargo',
    'node_license',
    'embargo_termination_approval',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields + fk_retraction_fields
user_key_blacklist = [
    '__backrefs',
    '_version',
    'affiliated_institutions',
    # '_affiliated_institutions',
    'watched',
    'external_accounts',
    'email_last_sent',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields


def build_query(fields, model):
    if model == MODMNode:
        queries = [
            (MQ('is_registration', 'eq', False)),
            (MQ('is_collection', 'eq', False)),
        ]
    else:
        queries = []
    queries.extend(list(MQ(field, 'ne', None)
               for field in list(set(fields) & set(model._fields.keys()))))
    if queries == []:
        return None
    return functools.reduce(operator.and_, queries)

def save_bare_institutions(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMNode.find(MQ('institution_id', 'ne', None), allow_institution=True).count()

    while count < total:
        with transaction.atomic():
            institutions = []
            for modm_node in MODMNode.find(MQ('institution_id', 'ne', None), allow_institution=True).sort('-date_modified')[count:count+page_size]:

                institutions.append(Institution.migrate_from_modm(modm_node))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving institutions {} through {}...'.format(
                        count - page_size, count
                    ))
                    woot = Institution.objects.bulk_create(institutions)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print('Done with {} institutions in {} seconds...'.format(
                        len(woot), (now - then).total_seconds()
                    ))
                    institutions = []
                    trash = gc.collect()
                    print('Took out {} trashes'.format(trash))
    print('MODM Institutions: {}'.format(total))
    print('django institutions: {}'.format(Institution.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare_registrations(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMNode.find(MQ('is_registration', 'eq', True), allow_institution=False).count()
    while count < total:
        with transaction.atomic():
            registrations = []
            for modm_node in MODMNode.find(MQ('is_registration', 'eq', True), allow_institution=False).sort(
                    '-date_modified')[count:count + page_size]:

                registrations.append(Registration.migrate_from_modm(modm_node))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving registrations {} through {}...'.format(
                        count - page_size, count
                    ))
                    woot = Registration.objects.bulk_create(registrations)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print('Done with {} registrations in {} seconds...'.format(
                        len(woot), (now - then).total_seconds()
                    ))
                    registrations = []
                    trash = gc.collect()
                    print('Took out {} trashes'.format(trash))
    print('MODM Registrations: {}'.format(total))
    print('django registrations: {}'.format(Registration.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare_collections(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMNode.find(MQ('is_collection', 'eq', True), allow_institution=False).count()
    while count < total:
        with transaction.atomic():
            collections = []
            for modm_node in MODMNode.find(MQ('is_collection', 'eq', True), allow_institution=False).sort(
                    '-date_modified')[count:count + page_size]:

                collections.append(Collection.migrate_from_modm(modm_node))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving collections {} through {}...'.format(
                        count - page_size, count
                    ))
                    woot = Collection.objects.bulk_create(collections)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print('Done with {} collections in {} seconds...'.format(
                        len(woot), (now - then).total_seconds()
                    ))
                    collections = []
                    trash = gc.collect()
                    print('Took out {} trashes'.format(trash))
    print('MODM Collections: {}'.format(total))
    print('django collections: {}'.format(Collection.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare(modm_model, django_model, page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = modm_model.find().count()

    while count < total:
        with transaction.atomic():
            django_objs = []
            page_of_modm_objects = modm_model.find()[count:count+page_size]
            for modm_obj in page_of_modm_objects:
                django_objs.append(django_model.migrate_from_modm(modm_obj))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving {} {} through {}...'.format(type(django_model), count - page_size, count))
                    saved_django_objs = django_model.objects.bulk_create(django_objs)
                    for django_instance in saved_django_objs:
                        if isinstance(django_instance, ObjectIDMixin):
                            modm_to_django[django_instance.guid] = django_instance.pk
                        elif isinstance(django_instance, GuidMixin):
                            modm_to_django[django_instance._guid.guid] = django_instance.pk
                        # TODO Find a better way to handle oddballs
                        elif isinstance(django_instance, Conference):
                            modm_to_django[django_instance.endpoint] = django_instance.pk
                        elif isinstance(django_instance, MetaSchema):
                            modm_to_django[django_instance.guid] = django_instance.pk
                        else:
                            print('What is this? It hasn\'t got a guid or a _guid.')
                            import ipdb
                            ipdb.set_trace()
                    now = datetime.now()
                    print('Done with {} {} in {} seconds...'.format(len(saved_django_objs), type(django_model), (now - then).total_seconds()))
                    saved_django_objs = []
                    page_of_modm_objects = []
                    print('Took out {} trashes'.format(gc.collect()))


def save_bare_nodes(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMNode.find(functools.reduce(operator.and_, [
        MQ('is_registration', 'eq', False),
        MQ('is_collection', 'eq', False),
    ]), allow_institution=False).count()

    while count < total:
        with transaction.atomic():
            nids = []
            for modm_node in MODMNode.find(functools.reduce(operator.and_, [
                    MQ('is_registration', 'eq', False),
                    MQ('is_collection', 'eq', False),
                ]), allow_institution=False).sort('-date_modified')[count:count + page_size]:
                nids.append(Node.migrate_from_modm(modm_node))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving nodes {} through {}...'.format(
                        count - page_size, count))
                    woot = Node.objects.bulk_create(nids)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print('Done with {} nodes in {} seconds...'.format(
                        len(woot), (now - then).total_seconds()))
                    nids = []
                    trash = gc.collect()
                    print('Took out {} trashes'.format(trash))

    print('Modm Nodes: {}'.format(total))
    print('django Nodes: {}'.format(Node.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def merge_duplicate_users():
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    start = datetime.now()

    from framework.mongo.handlers import database

    duplicates = database.user.aggregate([
        {
            "$group": {
                "_id": "$username",
                "ids": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]).get('result')
    # [
    #   {
    #       'count': 5,
    #       '_id': 'duplicated@username.com',
    #       'ids': [
    #           'listo','fidst','hatma','tchth','euser','name!'
    #       ]
    #   }
    # ]
    print('Found {} duplicate usernames.'.format(len(duplicates)))
    for duplicate in duplicates:
        print('Found {} copies of {}'.format(len(duplicate.get('ids')), duplicate.get('_id')))
        if duplicate.get('_id'):
            # _id is an email address, merge users keeping the one that was logged into last
            users = list(MODMUser.find(MQ('_id', 'in', duplicate.get('ids'))).sort('-last_login'))
            best_match = users.pop()
            for user in users:
                print('Merging user {} into user {}'.format(user._id, best_match._id))
                best_match.merge_user(user)
        else:
            # _id is null, set all usernames to their guid
            users = MODMUser.find(MQ('_id', 'in', duplicate.get('ids')))
            for user in users:
                print('Setting username for {}'.format(user._id))
                user.username = user._id
                user.save()
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare_users(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMUser.find().count()

    while count < total:
        with transaction.atomic():
            users = []
            for modm_user in MODMUser.find().sort('-date_registered')[
                    count:count + page_size]:
                users.append(OSFUser.migrate_from_modm(modm_user))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving users {} through {}...'.format(
                        count - page_size, count))
                    try:
                        woot = OSFUser.objects.bulk_create(users)
                    except Exception as ex:
                        import ipdb
                        ipdb.set_trace()
                    else:
                        for wit in woot:
                            modm_to_django[wit._guid.guid] = wit.pk
                        now = datetime.now()
                        print('Done with {} users in {} seconds...'.format(
                            len(woot), (now - then).total_seconds()))
                        users = None
                        woot = None
                        guid = None
                        user_fields = None
                        cleaned_user_fields = None
                        trash = gc.collect()
                        print('Took out {} trashes'.format(trash))

    print('Modm Users: {}'.format(total))
    print('django Users: {}'.format(OSFUser.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare_tags(page_size=5000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    count = 0
    start = datetime.now()
    total = MODMTag.find().count()

    while count < total:
        with transaction.atomic():
            tags = []
            for modm_tag in MODMTag.find().sort('-_id')[count:count +
                                                        page_size]:
                tags.append(Tag(_id=modm_tag._id,
                                lower=modm_tag.lower,
                                system=False))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print('Saving tags {} through {}...'.format(
                        count - page_size, count))
                    woot = Tag.objects.bulk_create(tags)
                    now = datetime.now()
                    print('Done with {} tags in {} seconds...'.format(
                        len(woot), (now - then).total_seconds()))
                    tags = None
                    woot = None
                    trash = gc.collect()
                    print('Took out {} trashes'.format(trash))

    print('MODM Tags: {}'.format(total))
    print('django Tags: {}'.format(Tag.objects.all().count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def save_bare_system_tags(page_size=10000):
    print('Starting save_bare_system_tags...')
    start = datetime.now()

    things = list(MODMNode.find(MQ('system_tags', 'ne', [])).sort(
        '-_id')) + list(MODMUser.find(MQ('system_tags', 'ne', [])).sort(
            '-_id'))

    system_tag_ids = []
    for thing in things:
        for system_tag in thing.system_tags:
            system_tag_ids.append(system_tag)

    unique_system_tag_ids = set(system_tag_ids)

    total = len(unique_system_tag_ids)

    system_tags = []
    for system_tag_id in unique_system_tag_ids:
        system_tags.append(Tag(_id=system_tag_id,
                               lower=system_tag_id.lower(),
                               system=True))

    woot = Tag.objects.bulk_create(system_tags)

    print('MODM System Tags: {}'.format(total))
    print('django system tags: {}'.format(Tag.objects.filter(system=
                                                              True).count()))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))

def set_node_foreign_keys_on_nodes(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(fk_node_fields, MODMNode),
        allow_institution=False).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(fk_node_fields, MODMNode),
                    allow_institution=False).sort('-date_modified')[
                        node_count:node_count + page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_node_field in fk_node_fields:
                    value = getattr(modm_node, fk_node_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                node_id = Node.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field), node_id)
                                # save for later
                                modm_to_django[value] = node_id
                                cache_misses += 1
                        elif isinstance(value, MODMNode):
                            # value is a node object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                node_id = Node.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field), node_id)
                                # save for later
                                modm_to_django[value._id] = node_id
                                cache_misses += 1
                        else:
                            # whu happened?
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    then = datetime.now()
                    print('Through {} nodes and {} foreign keys'.format(
                        node_count, fk_count))
                    print('Cache: Hits {} Misses {}'.format(cache_hits,
                                                             cache_misses))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_retraction_foreign_keys_on_nodes(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(build_query(fk_retraction_fields, MODMNode), allow_institution=False).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(build_query(fk_retraction_fields, MODMNode), allow_institution=False).sort('-date_modified')[node_count:node_count+page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_retraction_field in fk_retraction_fields:
                    value = getattr(modm_node, fk_retraction_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            if value in modm_to_django:
                                setattr(django_node, '{}_id'.format(fk_retraction_field), modm_to_django[value])
                                cache_hits += 1
                            else:
                                retraction_id = Retraction.objects.get(guid=value).pk
                                setattr(django_node, '{}_id'.format(fk_retraction_field), retraction_id)
                                modm_to_django[value] = retraction_id
                                cache_misses += 1
                        elif isinstance(value, MODMRetraction):
                            if value._id in modm_to_django:
                                setattr(django_node, '{}_id'.format(fk_retraction_field), modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                retraction_id = Retraction.objects.get(guid=value._id).pk
                                setattr(django_node, '{}_id'.format(fk_retraction_field), retraction_id)
                                modm_to_django[value] = retraction_id
                                cache_misses += 1
                        else:
                            # whu happened?
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb

                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} foreign keys'.format(node_count, fk_count))
                    print('Cache: Hits {} Misses {}'.format(cache_hits, cache_misses))
    print(
    'Done with {} in {} seconds...'.format(sys._getframe().f_code.co_name, (datetime.now() - start).total_seconds()))


def set_embargo_foreign_keys_on_nodes(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(build_query(fk_embargo_fields, MODMNode), allow_institution=False).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(build_query(fk_embargo_fields, MODMNode), allow_institution=False).sort(
                    '-date_modified')[node_count:node_count + page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_embargo_field in fk_embargo_fields:
                    value = getattr(modm_node, fk_embargo_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            if value in modm_to_django:
                                setattr(django_node, '{}_id'.format(fk_embargo_field), modm_to_django[value])
                                cache_hits += 1
                            else:
                                embargo_id = Embargo.objects.get(guid=value).pk
                                setattr(django_node, '{}_id'.format(fk_embargo_field), embargo_id)
                                modm_to_django[value] = embargo_id
                                cache_misses += 1
                        elif isinstance(value, MODMEmbargo):
                            if value._id in modm_to_django:
                                setattr(django_node, '{}_id'.format(fk_embargo_field), modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                embargo_id = Embargo.objects.get(guid=value._id).pk
                                setattr(django_node, '{}_id'.format(fk_embargo_field), embargo_id)
                                modm_to_django[value._id] = embargo_id
                                cache_misses += 1
                        else:
                            # whu happened?
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb

                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} foreign keys'.format(node_count, fk_count))
                    print('Cache: Hits {} Misses {}'.format(cache_hits, cache_misses))
    print('Done with {} in {} seconds...'.format(sys._getframe().f_code.co_name,
                                                  (datetime.now() - start).total_seconds()))


def set_user_foreign_keys_on_nodes(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(fk_user_fields, MODMNode),
        allow_institution=False).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(fk_user_fields, MODMNode),
                    allow_institution=False).sort('-date_modified')[
                        node_count:node_count + page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_user_field in fk_user_fields:
                    value = getattr(modm_node, fk_user_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = OSFUser.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value] = user_id
                                cache_misses += 1
                        elif isinstance(value, MODMUser):
                            # value is a node object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = OSFUser.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value._id] = user_id
                                cache_misses += 1
                        else:
                            # that's odd.
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} foreign keys'.format(
                        node_count, fk_count))
                    print('Cache: Hits {} Misses {}'.format(cache_hits,
                                                             cache_misses))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_user_foreign_keys_on_users(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    user_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMUser.find(build_query(fk_user_fields, MODMUser)).count()

    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    fk_user_fields, MODMUser)).sort('-date_registered')[
                        user_count:user_count + page_size]:
                django_user = OSFUser.objects.get(_guid__guid=modm_user._id)
                for fk_user_field in fk_user_fields:
                    value = getattr(modm_user, fk_user_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = OSFUser.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value] = user_id
                                cache_misses += 1
                        elif isinstance(value, MODMUser):
                            # value is a user object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = OSFUser.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value._id] = user_id
                                cache_misses += 1
                        else:
                            # that's odd.
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_user.save()
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print('Through {} users and {} foreign keys'.format(
                        user_count, fk_count))
                    print('Cache: Hits {} Misses {}'.format(cache_hits,
                                                             cache_misses))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_node_many_to_many_on_nodes(page_size=5000):
    modm_to_django = build_pk_caches()
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(m2m_node_fields, MODMNode),
        allow_institution=False).count()
    print('{} Nodes'.format(total))

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(m2m_node_fields, MODMNode),
                    allow_institution=False).sort('-date_modified')[
                        node_count:page_size + node_count]:
                try:
                    django_node = Node.objects.get(
                        pk=modm_to_django[modm_node._id])
                except (Node.DoesNotExist, KeyError):
                    print('BROKEN modm_node._id: {} pk: {}'.format(modm_node._id, modm_to_django[modm_node._id]))
                    raise
                for m2m_node_field in m2m_node_fields:
                    m2m_django_node_field = m2m_node_field
                    if m2m_node_field.startswith('_'):
                        m2m_django_node_field = m2m_node_field[1:]

                    attr = getattr(django_node, m2m_django_node_field)
                    django_pks = []
                    for modm_m2m_value in getattr(modm_node, m2m_node_field,
                                                  []):
                        if isinstance(modm_m2m_value, MODMNode):
                            django_pks.append(modm_to_django[
                                modm_m2m_value._id])
                        elif isinstance(modm_m2m_value, basestring):
                            django_pks.append(modm_to_django[modm_m2m_value])
                        elif isinstance(modm_m2m_value, Pointer):
                            django_pks.append(modm_to_django[
                                modm_m2m_value.node._id])
                        else:
                            # wth
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb
                            bpdb.set_trace()
                    if len(django_pks) > 0:
                        attr.add(*django_pks)
                    m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} m2m'.format(node_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_user_many_to_many_on_nodes(page_size=5000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(m2m_user_fields, MODMNode),
        allow_institution=False).count()
    print('{} Nodes'.format(total))
    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(m2m_user_fields, MODMNode),
                    allow_institution=False).sort('-date_modified')[
                        node_count:page_size + node_count]:
                django_node = Node.objects.get(
                    pk=modm_to_django[modm_node._id])
                for m2m_user_field in m2m_user_fields:
                    if m2m_user_field in ['permissions', 'recently_added']:
                        continue
                    attr = getattr(django_node, m2m_user_field)
                    django_pks = []

                    try:
                        modm_user_value = getattr(modm_node, m2m_user_field, [])
                    except Exception as ex:
                        import ipdb
                        ipdb.set_trace()
                        modm_user_value = []

                    for modm_m2m_value in modm_user_value:
                        if isinstance(modm_m2m_value, MODMUser):
                            if m2m_user_field == 'contributors':
                                visible = modm_m2m_value._id in modm_node.visible_contributor_ids
                                admin = 'admin' in modm_node.permissions[
                                    modm_m2m_value._id]
                                read = 'read' in modm_node.permissions[
                                    modm_m2m_value._id]
                                write = 'write' in modm_node.permissions[
                                    modm_m2m_value._id]

                                Contributor.objects.get_or_create(
                                    user_id=modm_to_django[modm_m2m_value._id],
                                    node=django_node,
                                    visible=visible,
                                    admin=admin,
                                    read=read,
                                    write=write)
                                m2m_count += 1
                            else:
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                        elif isinstance(modm_m2m_value, basestring):
                            if m2m_user_field == 'contributors':
                                visible = modm_m2m_value in modm_node.visible_contributor_ids
                                admin = 'admin' in modm_node.permissions[
                                    modm_m2m_value]
                                read = 'read' in modm_node.permissions[
                                    modm_m2m_value]
                                write = 'write' in modm_node.permissions[
                                    modm_m2m_value]
                                Contributor.objects.get_or_create(
                                    user_id=modm_to_django[modm_m2m_value],
                                    node=django_node,
                                    visible=visible,
                                    admin=admin,
                                    read=read,
                                    write=write)
                                m2m_count += 1
                            else:
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                        else:
                            # wth
                            print('\a')  # bells
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            print('\a')
                            import bpdb
                            bpdb.set_trace()

                    if len(django_pks) > 0:
                        attr.add(*django_pks)
                    m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} m2m'.format(node_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_node_many_to_many_on_users(page_size=5000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_node_fields, MODMUser)).count()
    print('{} Users'.format(total))
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_node_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = OSFUser.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_node_field in m2m_node_fields:
                    try:
                        attr = getattr(django_user, m2m_node_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user,
                                                      m2m_node_field, []):
                            if isinstance(modm_m2m_value, MODMNode):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                            elif isinstance(modm_m2m_value, Pointer):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value.node._id])
                            else:
                                # wth
                                print('\a')  # bells!
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                import bpdb
                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print('Through {} users and {} m2m'.format(user_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_user_many_to_many_on_users(page_size=5000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_user_fields, MODMUser)).count()
    print('{} Users'.format(total))
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_user_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = OSFUser.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_user_field in m2m_user_fields:
                    try:
                        attr = getattr(django_user, m2m_user_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user,
                                                      m2m_user_field, []):
                            if isinstance(modm_m2m_value, MODMUser):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                            else:
                                # wth
                                print('\a')  # bells!
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print('Through {} users and {} m2m'.format(user_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_system_tag_many_to_many_on_users(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_tag_fields, MODMUser)).count()
    print('{} Users'.format(total))
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_tag_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = OSFUser.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_tag_field in m2m_tag_fields:
                    try:
                        attr = getattr(django_user, m2m_tag_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user, m2m_tag_field,
                                                      []):
                            if isinstance(modm_m2m_value, MODMTag):
                                django_pks.append(modm_to_django[
                                    '{}:system'.format(modm_m2m_value)])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    '{}:system'.format(modm_m2m_value)])
                            else:
                                # wth
                                print('\a')  # bells!
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print('Through {} users and {} m2m'.format(user_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def set_tag_many_to_many_on_nodes(page_size=10000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(build_query(m2m_tag_fields, MODMNode)).count()
    print('{} Nodes'.format(total))
    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(build_query(
                    m2m_tag_fields, MODMNode), allow_institution=False).sort('-date_modified')[
                        node_count:page_size + node_count]:
                django_node = Node.objects.get(
                    pk=modm_to_django[modm_node._id])
                for m2m_tag_field in m2m_tag_fields:
                    try:
                        attr = getattr(django_node, m2m_tag_field)
                    except AttributeError as ex:
                        # node field doesn't exist on node
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_node, m2m_tag_field,
                                                      []):
                            suffix = 'system' if m2m_tag_field == 'system_tags' else 'not_system'
                            if isinstance(modm_m2m_value, MODMTag):
                                django_pks.append(modm_to_django[
                                    '{}:{}'.format(modm_m2m_value._id,
                                                   suffix)])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    '{}:{}'.format(modm_m2m_value, suffix)])
                            elif modm_m2m_value is None:
                                print('Tag of None found on Node {}'.format(
                                    modm_node._id))
                            else:
                                # wth
                                print('\a')  # bells!
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                print('\a')
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print('Through {} nodes and {} m2m'.format(node_count,
                                                                m2m_count))
    print('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds()))


def build_pk_caches():
    # build a lookup table of all guids to pks
    modm_to_django = {x['_guid__guid']: x['pk'] for x in Node.objects.all().values('_guid__guid', 'pk')}
    modm_to_django.update({x['_guid__guid']: x['pk'] for x in Institution.objects.all().values('_guid__guid', 'pk')})
    modm_to_django.update({x['_guid__guid']: x['pk'] for x in OSFUser.objects.all().values('_guid__guid', 'pk')})
    modm_to_django.update({'{}:system'.format(x['_id']): x['pk'] for x in Tag.objects.filter(system=True).values('_id', 'pk')})
    modm_to_django.update({'{}:not_system'.format(x['_id']): x['pk'] for x in Tag.objects.filter(system=False).values('_id', 'pk')})
    modm_to_django.update({x['guid']: x['pk'] for x in Embargo.objects.all().values('guid', 'pk')})
    modm_to_django.update({x['guid']: x['pk'] for x in Retraction.objects.all().values('guid', 'pk')})
    return modm_to_django


global modm_to_django
modm_to_django = build_pk_caches()
print('Cached {} MODM to django mappings...'.format(len(modm_to_django.keys())))
