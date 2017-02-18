from __future__ import unicode_literals

import gc
import importlib
import logging
import pstats
import sys
from cProfile import Profile

import ipdb
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from modularodm import Q as MQ
from psycopg2._psycopg import AsIs
from typedmodels.models import TypedModel

from addons.wiki.models import NodeWikiPage
from api.base.celery import app
from framework import encryption
from framework.auth.core import User as MODMUser
from framework.mongo import database
from framework.mongo import set_up_storage
from framework.mongo import storage
from framework.transactions.context import transaction as modm_transaction
from osf.models import Comment
from osf.models import Institution
from osf.models import (NodeLog, OSFUser,
                        PageCounter, StoredFileNode, Tag, UserActivityCounter)
from osf.models.base import Guid, GuidMixin, OptionalGuidMixin
from osf.models.node import AbstractNode
from osf.utils.order_apps import get_ordered_models
from website.addons.osfstorage.model import OsfStorageNodeSettings
from website.addons.wiki.model import NodeWikiPage as MODMNodeWikiPage, AddonWikiNodeSettings
from website.app import init_app
from website.files.models import StoredFileNode as MODMStoredFileNode
from website.models import Comment as MODMComment
from website.models import Guid as MGuid
from website.models import Node as MODMNode
from website.models import User as MUser
from website.oauth.models import ApiOAuth2Scope

logger = logging.getLogger('migrations')

encryption.encrypt = lambda x: x
encryption.decrypt = lambda x: x


def set_backend():
    # monkey patch field aliases for migration
    Institution.FIELD_ALIASES = {
        'institution_auth_url': 'login_url',
        'institution_logout_url': 'logout_url',
        'title': 'name',
        '_id': False,
        'institution_id': '_id',
        'institution_banner_name': 'banner_name',
        'institution_domains': 'domains',
        'institution_email_domains': 'email_domains',
        'institution_logo_name': 'logo_name',
    }
    StoredFileNode.FIELD_ALIASES = {
        '_materialized_path': 'materialized_path'
    }
    set_up_storage([ApiOAuth2Scope], storage.MongoStorage)


def get_modm_model(django_model):
    module_path, model_name = django_model.modm_model_path.rsplit('.', 1)
    modm_module = importlib.import_module(module_path)
    return getattr(modm_module, model_name)


@app.task()
def migrate_page_counters(page_size=20000):
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))
    collection = database['pagecounters']

    total = collection.count()
    count = 0
    start_time = timezone.now()
    while count < total:
        with transaction.atomic():
            django_objects = []
            offset = count
            limit = (count + page_size) if (count + page_size) < total else total

            page_of_modm_objects = collection.find().sort('_id', 1)[offset:limit]
            for mongo_obj in page_of_modm_objects:
                django_objects.append(PageCounter(_id=mongo_obj['_id'], date=mongo_obj['date'], total=mongo_obj['total'], unique=mongo_obj['unique']))
                count += 1

                if count % page_size == 0 or count == total:
                    page_finish_time = timezone.now()
                    if (count - page_size) < 0:
                        start = 0
                    else:
                        start = count - page_size
                    logger.info('Saving {} {} through {}...'.format(PageCounter._meta.model.__module__, start, count))

                    saved_django_objects = PageCounter.objects.bulk_create(django_objects)

                    logger.info('Done with {} {} in {} seconds...'.format(len(saved_django_objects), PageCounter._meta.model.__module__, (timezone.now()-page_finish_time).total_seconds()))
                    saved_django_objects = []
    total = None
    count = None
    logger.info('Finished {} in {} seconds...'.format(sys._getframe().f_code.co_name, (timezone.now()-start_time).total_seconds()))


@app.task()
def migrate_user_activity_counters(page_size=20000):
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))
    collection = database['useractivitycounters']

    total = collection.count()
    count = 0
    start_time = timezone.now()
    while count < total:
        with transaction.atomic():
            django_objects = []
            offset = count
            limit = (count + page_size) if (count + page_size) < total else total

            page_of_modm_objects = collection.find().sort('_id', 1)[offset:limit]
            for mongo_obj in page_of_modm_objects:
                django_objects.append(UserActivityCounter(_id=mongo_obj['_id'], date=mongo_obj['date'], total=mongo_obj['total'], action=mongo_obj['action']))
                count += 1

                if count % page_size == 0 or count == total:
                    page_finish_time = timezone.now()
                    if (count - page_size) < 0:
                        start = 0
                    else:
                        start = count - page_size
                    logger.info('Saving {} {} through {}...'.format(UserActivityCounter._meta.model.__module__, start, count))

                    saved_django_objects = UserActivityCounter.objects.bulk_create(django_objects)

                    logger.info('Done with {} {} in {} seconds...'.format(len(saved_django_objects), UserActivityCounter._meta.model.__module__, (timezone.now()-page_finish_time).total_seconds()))
                    saved_django_objects = []
    total = None
    count = None
    logger.info('Finished {} in {} seconds...'.format(sys._getframe().f_code.co_name, (timezone.now()-start_time).total_seconds()))


@app.task()
def make_guids():
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))

    guid_models = [model for model in get_ordered_models() if (issubclass(model, GuidMixin) or issubclass(model, OptionalGuidMixin)) and (not issubclass(model, AbstractNode) or model is AbstractNode)]

    with connection.cursor() as cursor:
        with transaction.atomic():
            for model in guid_models:
                with transaction.atomic():
                    content_type = ContentType.objects.get_for_model(model)
                    if issubclass(model, TypedModel):
                        sql = """
                                INSERT INTO osf_guid
                                    (
                                        _id,
                                        object_id,
                                        created,
                                        content_type_id
                                    )
                                SELECT DISTINCT ON (guid_string)
                                  guid,
                                  t.id,
                                  clock_timestamp(),
                                  t.content_type_pk
                                FROM
                                  {}_{} AS t,
                                  UNNEST(t.guid_string) AS guid
                                WHERE
                                  t.guid_string IS NOT NULL AND
                                  t.content_type_pk IS NOT NULL
                                ORDER BY
                                  t.guid_string, type DESC;
                              """.format(content_type.app_label, content_type.model)
                    else:
                        sql = """
                                INSERT INTO osf_guid
                                    (
                                        _id,
                                        object_id,
                                        created,
                                        content_type_id
                                    )
                                SELECT
                                  guid,
                                  t.id,
                                  clock_timestamp(),
                                  t.content_type_pk
                                FROM
                                  {}_{} AS t,
                                  UNNEST(t.guid_string) AS guid
                                WHERE
                                  t.guid_string IS NOT NULL AND
                                  t.content_type_pk IS NOT NULL;
                              """.format(content_type.app_label, content_type.model)
                    logger.info('Making guids for {}'.format(model._meta.model.__module__))
                    try:
                        cursor.execute(sql)
                    except IntegrityError as ex:
                        ipdb.set_trace()

            guids = MGuid.find(MQ('is_orphaned', 'ne', True))
            guid_keys = guids.get_keys()
            orphaned_guids = []
            for g in guids:
                try:
                    # if it's one of the abandoned models add it to orphaned_guids
                    if g.to_storage()['referent'][1] in ['dropboxfile', 'osfstorageguidfile', 'osfguidfile',
                                                         'githubguidfile', 'nodefile', 'boxfile',
                                                         'figshareguidfile', 's3guidfile', 'dataversefile']:
                        orphaned_guids.append(unicode(g._id))
                except TypeError:
                    pass
            # orphaned_guids = [unicode(g._id) for g in guids if g is not None and g.to_storage() is not None and len(g.to_storage['referent']) > 0 and g.to_storage()['referent'][1] in ['dropboxfile', 'osfstorageguidfile', 'osfguidfile', 'githubguidfile', 'nodefile', 'boxfile', 'figshareguidfile', 's3guidfile', 'dataversefile']]
            # get all the guids in postgres
            existing_guids = Guid.objects.all().values_list('_id', flat=True)
            # subtract the orphaned guids from the guids in modm and from that subtract existing guids
            # that should give us the guids that are missing
            guids_to_make = (set(guid_keys) - set(orphaned_guids)) - set(existing_guids)
            logger.info('{} MODM Guids, {} Orphaned Guids, {} Guids to Make, {} Existing guids'.format(len(guid_keys), len(orphaned_guids), len(guids_to_make), len(existing_guids)))
            from django.apps import apps
            model_names = {m._meta.model.__module__.lower(): m._meta.model for m in apps.get_models()}

            with ipdb.launch_ipdb_on_exception():
                # loop through missing guids
                for guid in guids_to_make:
                    # load them from modm
                    guid_dict = MGuid.load(guid).to_storage()
                    # if they don't have a referent toss them
                    if guid_dict['referent'] is None:
                        logger.info('{} has no referent.'.format(guid))
                        continue
                    # get the model string from the referent
                    modm_model_string = guid_dict['referent'][1]
                    if modm_model_string == 'user':
                        modm_model_string = 'osfuser'
                    # if the model string is in our list of models load it up
                    if modm_model_string in model_names:
                        referent_model = model_names[modm_model_string]
                    else:
                        # this filters out bad models, like osfstorageguidfile
                        # but these should already be gone
                        logger.info('Couldn\'t find model for {}'.format(modm_model_string))
                        continue
                    # get the id from the to_storage dictionary
                    modm_model_id = guid_dict['_id']
                    # if it's something that should have a guid
                    if issubclass(referent_model, GuidMixin) or issubclass(referent_model, OptionalGuidMixin):
                        try:
                            # find it's referent
                            referent_instance = referent_model.objects.get(guid_string__contains=[modm_model_id.lower()])
                        except referent_model.DoesNotExist:
                            logger.info('Couldn\'t find referent for {}:{}'.format(referent_model._meta.model.__module__, modm_model_id))
                            continue
                    else:
                        # we shouldn't ever get here, bad data
                        logger.info('Found guid pointing at {} type, dropping it on the floor.'.format(modm_model_string))
                        continue

                    # if we got a referent instance create the guid
                    if referent_instance:
                        Guid.objects.create(referent=referent_instance)
                    else:
                        logger.info('{} {} didn\'t create a Guid'.format(referent_model._meta.model.__module__, modm_model_id))
            # TODO think about this for prod
            if orphaned_guids:
                logger.info('Started creating blacklist orphaned guids.')
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO
                          osf_blacklistguid
                          (guid)
                        VALUES %(guids)s ON CONFLICT DO NOTHING;
                    """
                    params = ''.join(['(\'{}\'), '.format(og) for og in orphaned_guids])[0:-2]
                    cursor.execute(sql, {'guids': AsIs(params)})


def validate_guid_referents_against_ids():
    import ipdb
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()
    with ipdb.launch_ipdb_on_exception():
        for django_model in [model for model in get_ordered_models() if (issubclass(model, GuidMixin) or issubclass(model, OptionalGuidMixin)) and (not issubclass(model, AbstractNode) or model is AbstractNode)]:
            if not hasattr(django_model, 'modm_model_path'):
                logger.info('################################################\n'
                            '{} doesn\'t have a modm_model_path\n'
                            '################################################'.format(
                    django_model._meta.model.__module__))
                continue
            modm_model = get_modm_model(django_model)
            model_name = django_model._meta.model.__module__.lower()
            if model_name == 'osfuser':
                model_name = 'user'

            logger.info('Starting {}...'.format(model_name))
            guids = modm_model.find().get_keys()
            for guid in guids:
                guid_instance = MGuid.load(guid)
                if not guid_instance:
                    # There is no guid instance for this guid string
                    if len(guid) > 5:
                        continue
                    logger.info('{}:{}\'s guid doesn\'t exist.'.format(model_name, guid))
                    import ipdb; ipdb.set_trace()
                    continue
                if not guid_instance.referent:
                    # the referent is not set
                    logger.info('{}:{}\'s referent is None.'.format(model_name, guid_instance._id))
                    # find the referent with the same _id and model_name
                    referent = modm_model.load(guid_instance._id)
                    if referent is not None:
                        guid.referent = referent
                        guid.save()
                        continue
                    print('Could not find referent for {}:{}'.format(referent_model_name, guid_instance._id))
                    continue
                referent_model_name = guid_instance.to_storage()['referent'][1]
                if referent_model_name != model_name:
                    # the referent isn't pointing at the correct type of object. Try and find the object it should be pointing to.
                    if referent_model_name == 'node' and model_name in ['node', 'abstractnode', 'registration', 'collection']:
                        # nodes have been broken out into separate models, treat these differently
                        continue

                    logger.info('{}:{}\'s referent doesn\'t match {}:{}'.format(referent_model_name, guid_instance.to_storage()['referent'][0], model_name, guid_instance._id))

            logger.info('Finished {}...'.format(model_name))
            modm_model._cache.clear()
            modm_model._object_cache.clear()
            gc.collect()

@app.task()
def fix_guids():
    modm_guids = MGuid.find().get_keys()
    dj_guids = Guid.objects.all().values_list('_id', flat=True)
    set_of_modm_guids = set(modm_guids)
    set_of_django_guids = set(dj_guids)
    missing = set_of_modm_guids - set_of_django_guids
    short_missing = [x for x in missing if len(x) < 6]
    long_missing = [x for x in missing if len(x) > 5]
    assert len(short_missing) + len(long_missing) == len(missing), 'It broke'
    # NOTE: is_orphaned will be True for Guids that should not be migrated because they have
    # invalid/missing referents
    short_missing_guids = MGuid.find(MQ('_id', 'in', short_missing) & MQ('is_orphaned', 'ne', True))
    long_missing_guids = MGuid.find(MQ('_id', 'in', long_missing) & MQ('is_orphaned', 'ne', True))

    short_missing_guids_with_referents = [x._id for x in short_missing_guids if x.referent is not None]
    short_missing_guids_without_referents = [x._id for x in short_missing_guids if x.referent is None]

    nodes = 0
    users = 0
    files = 0
    comments = 0
    wiki = 0
    missing = 0
    for guid in short_missing_guids.get_keys():
        user = MUser.load(guid)
        guid_instance = MGuid.load(guid)
        if user is not None:
            logger.info('Guid {} is a user.'.format(guid))
            guid_instance.referent = user
            guid_instance.save()

            try:
                # see if the existing guid exists
                existing_django_guid = Guid.objects.get(_id=unicode(guid).lower())
            except Guid.DoesNotExist:
                # try and get a user that has n+1 guids pointing at them
                try:
                    existing_django_guid = OSFUser.objects.get(guids___id=unicode(guid).lower())
                except OSFUser.DoesNotExist:
                    # create a new guid
                    existing_django_guid = Guid.migrate_from_modm(guid_instance)
                    existing_django_guid.save()

            users += 1
        else:
            node = MODMNode.load(guid)
            if node is not None:
                logger.info('Guid {} is a node.'.format(guid))
                guid_instance.referent = node
                guid_instance.save()
                try:
                    # see if the existing guid exists
                    existing_django_guid = Guid.objects.get(_id=unicode(guid).lower())
                except Guid.DoesNotExist:
                    # try and get a user that has n+1 guids pointing at them
                    try:
                        existing_django_guid = AbstractNode.objects.get(guids___id=unicode(guid).lower())
                    except AbstractNode.DoesNotExist:
                        # create a new guid
                        existing_django_guid = Guid.migrate_from_modm(guid_instance)
                        existing_django_guid.save()

                nodes += 1
            else:
                comment = MODMComment.load(guid)
                if comment is not None:
                    logger.info('Guid {} is a node.'.format(guid))
                    guid_instance.referent = comment
                    guid_instance.save()
                    try:
                        # see if the existing guid exists
                        existing_django_guid = Guid.objects.get(_id=unicode(guid).lower())
                    except Guid.DoesNotExist:
                        # try and get a user that has n+1 guids pointing at them
                        try:
                            existing_django_guid = Comment.objects.get(guids___id=unicode(guid).lower())
                        except AbstractNode.DoesNotExist:
                            # create a new guid
                            existing_django_guid = Guid.migrate_from_modm(guid_instance)
                            existing_django_guid.save()

                    comments += 1
                else:
                    sfn = MODMStoredFileNode.load(guid)
                    if sfn is not None:
                        logger.info('Guid {} is a file.'.format(guid))
                        guid_instance.referent = sfn
                        guid_instance.save()
                        try:
                            # see if the existing guid exists
                            existing_django_guid = Guid.objects.get(_id=unicode(guid).lower())
                        except Guid.DoesNotExist:
                            # try and get a user that has n+1 guids pointing at them
                            try:
                                existing_django_guid = StoredFileNode.objects.get(guids___id=unicode(guid).lower())
                            except StoredFileNode.DoesNotExist:
                                # create a new guid
                                existing_django_guid = Guid.migrate_from_modm(guid_instance)
                                existing_django_guid.save()

                        files += 1
                    else:
                        wiki = MODMNodeWikiPage.load(guid)
                        if wiki is not None:
                            logger.info('Guid {} is a file.'.format(guid))
                            guid_instance.referent = wiki
                            guid_instance.save()
                            try:
                                # see if the existing guid exists
                                existing_django_guid = Guid.objects.get(_id=unicode(guid).lower())
                            except Guid.DoesNotExist:
                                # try and get a user that has n+1 guids pointing at them
                                try:
                                    existing_django_guid = NodeWikiPage.objects.get(guids___id=unicode(guid).lower())
                                except StoredFileNode.DoesNotExist:
                                    # create a new guid
                                    existing_django_guid = Guid.migrate_from_modm(guid_instance)
                                    existing_django_guid.save()

                            wiki += 1
                        else:

                            if guid_instance.to_storage()['referent'] is not None:
                                logger.info('Guid {} does not match it\'s referent was a {}.'.format(guid,
                                                                                                     guid_instance.to_storage()[
                                                                                                         'referent'][
                                                                                                         1]))
                            else:
                                logger.info('Guid {} does not match it\'s referent was a {}.'.format(guid, None))
                            missing += 1
                            continue

    logger.info('Users: {}'.format(users))
    logger.info('Nodes: {}'.format(nodes))
    logger.info('Comments: {}'.format(comments))
    logger.info('Wiki: {}'.format(wiki))
    logger.info('Files: {}'.format(files))
    logger.info('Missing: {}'.format(missing))
    logger.info('Total: {}'.format(len(short_missing_guids)))

    guids_by_type = {}
    missing_referents = 0
    updated_referents = 0
    for guid in long_missing:
        guid_instance = MGuid.load(guid)
        if guid_instance is None:
            logger.info('Guid {} does not exist'.format(guid))
        elif guid_instance.referent is None:
            logger.info('Couldn\'t find referent for {}'.format(guid_instance._id))
            missing_referents += 1
        else:
            to_delete = ['nodelog', ]
            referent_type = guid_instance.to_storage()['referent'][1]
            if referent_type in to_delete:
                deleted = MGuid.remove(MQ('_id', 'eq', guid_instance._id))
                logger.info('Deleted guid {} of type {}'.format(guid, referent_type))
            if referent_type in guids_by_type:
                guids_by_type[guid_instance.to_storage()['referent'][1]] += 1
            else:
                guids_by_type[guid_instance.to_storage()['referent'][1]] = 1
    logger.info(guids_by_type)
    logger.info('Missing referents: {}'.format(missing_referents))
    logger.info('Updated referents: {}'.format(updated_referents))


@app.task()
def save_page_of_bare_models(django_model, offset, limit):
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()

    hashes = set()
    count = 0

    modm_model = get_modm_model(django_model)
    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)

    modm_page = modm_queryset.sort('-_id')[offset: limit]

    with transaction.atomic():
        django_objects = list()
        if not hasattr(django_model, '_natural_key'):
            logger.info('{}.{} is missing a natural key!'.format(django_model._meta.model.__module__,
                                                                 django_model._meta.model.__name__))

        for modm_obj in modm_page:
            # TODO should we do the same for files relating to an institution?
            # If we're migrating a NodeSetting pointing at an institution continue
            if isinstance(modm_obj, (AddonWikiNodeSettings,
                                     OsfStorageNodeSettings)) and modm_obj.owner is not None and modm_obj.owner.institution_id is not None:
                continue
            django_instance = django_model.migrate_from_modm(modm_obj)
            if django_instance is None:
                continue
            if django_instance._natural_key() is not None:
                # if there's a natural key
                if isinstance(django_instance._natural_key(), list):
                    found = []
                    for nk in django_instance._natural_key():
                        if nk not in hashes:
                            hashes.add(nk)
                        else:
                            found.append(nk)
                    if not found:
                        django_objects.append(django_instance)
                    else:
                        count += 1
                        logger.info(
                            '{}.{} with guids {} was already in hashes'.format(django_instance._meta.model.__module__,
                                                                               django_instance._meta.model.__name__,
                                                                               found))
                        continue
                else:
                    if django_instance._natural_key() not in hashes:
                        # and that natural key doesn't exist in hashes
                        # add it to hashes and append the object
                        hashes.add(django_instance._natural_key())
                        django_objects.append(django_instance)
                    else:
                        count += 1
                        continue
            else:
                django_objects.append(django_instance)

            count += 1
        page_finish_time = timezone.now()
        logger.info(
            'Saving {} of {}.{}...'.format(count, django_model._meta.model.__module__, django_model._meta.model.__name__))
        if len(django_objects) > 1000:
            batch_size = len(django_objects) // 5
        else:
            batch_size = len(django_objects)
        saved_django_objects = django_model.objects.bulk_create(django_objects, batch_size=batch_size)

        logger.info('Done with {} {}.{} in {} seconds...'.format(len(saved_django_objects),
                                                                 django_model._meta.model.__module__,
                                                                 django_model._meta.model.__name__, (
                                                                     timezone.now() -
                                                                     page_finish_time).total_seconds()))
        modm_obj._cache.clear()
        modm_obj._object_cache.clear()
        saved_django_objects = []
        page_of_modm_objects = []
    total = None
    count = None
    hashes = None


@app.task()
def save_bare_models(django_model):
    logger.info('Starting {} on {}.{}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__module__, django_model._meta.model.__name__))
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()
    count = 0
    modm_model = get_modm_model(django_model)
    page_size = django_model.migration_page_size

    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)
    total = modm_queryset.count()

    while count < total:
        logger.info('{}.{} starting'.format(django_model._meta.model.__module__, django_model._meta.model.__name__))
        save_page_of_bare_models.delay(django_model, count, count+page_size)
        count += page_size


class DuplicateExternalAccounts(Exception):
    pass


@app.task()
def save_bare_system_tags(page_size=10000):
    logger.info('Starting save_bare_system_tags...')
    start = timezone.now()

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
        system_tags.append(Tag(name=system_tag_id,
                               system=True))

    Tag.objects.bulk_create(system_tags)

    logger.info('MODM System Tags: {}'.format(total))
    logger.info('django system tags: {}'.format(Tag.objects.filter(system=True).count()))
    logger.info('Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (timezone.now() - start).total_seconds()))


def register_nonexistent_models_with_modm():
    """
    There are guids refering to models that no longer exist.
    We can't delete the guids because then they could be regenerated.
    These models are registered so that anything at all will work.
    :return:
    """

    class DropboxFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class OSFStorageGuidFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class OSFGuidFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class GithubGuidFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class NodeFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class BoxFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class FigShareGuidFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class S3GuidFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    class DataverseFile(MODMStoredFileNode):
        _primary_key = '_id'
        pass

    DataverseFile.register_collection()
    NodeFile.register_collection()
    S3GuidFile.register_collection()
    FigShareGuidFile.register_collection()
    BoxFile.register_collection()
    GithubGuidFile.register_collection()
    OSFStorageGuidFile.register_collection()
    OSFGuidFile.register_collection()
    DropboxFile.register_collection()


@modm_transaction()
def ensure_no_duplicate_users():
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))
    start = timezone.now()

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
    if duplicates:
        raise AssertionError('Duplicate usernames found: {}. '
                             'Use the scripts.merge_duplicate_users and '
                             'scripts.set_null_usernames_to_guid scripts '
                             'to ensure uniqueness.'.format(duplicates))

def find_duplicate_addon_user_settings():
    COLLECTIONS = [
        'addondataverseusersettings',
        'addonfigshareusersettings',
        # 'addongithubusersettings',  # old, unused
        'addonowncloudusersettings',
        # 'addons3usersettings',  # old, unused
        'boxusersettings',
        'dropboxusersettings',
        'githubusersettings',
        'googledriveusersettings',
        'mendeleyusersettings',
        'osfstorageusersettings',
        's3usersettings',
        'zoterousersettings',
        'addonwikiusersettings'
    ]
    for collection in COLLECTIONS:
        targets = database[collection].aggregate([
            {
                '$group': {
                    '_id': '$owner',
                    'ids': {'$addToSet': '$_id'},
                    'count': {'$sum': 1}
                }
            },
            {
                '$match': {
                    'count': {'$gt': 1}
                }
            },
            {
                '$sort': {
                    'count': -1
                }
            }
        ]).get('result')
        if targets:
            raise AssertionError(
                'Multiple {} records associated with users: {}. '
                'Use scripts.clean_invalid_addon_settings to fix this issue.'.format(
                    collection, ', '.join([each['_id'] for each in targets])
                )
            )

def find_duplicate_addon_node_settings():
    COLLECTIONS = [
        'addondataversenodesettings',
        'addonfigsharenodesettings',
        # 'addongithubnodesettings',  # old, unused
        'addonowncloudnodesettings',
        # 'addons3nodesettings',  # old, unused
        'boxnodesettings',
        'figsharenodesettings',
        'dropboxnodesettings',
        'githubnodesettings',
        'googledrivenodesettings',
        'mendeleynodesettings',
        'osfstoragenodesettings',
        's3nodesettings',
        'zoteronodesettings',
        'addonwikinodesettings',
        'forwardnodesettings',
    ]

    for collection in COLLECTIONS:
        targets = database[collection].aggregate([
            {
                '$group': {
                    '_id': '$owner',
                    'ids': {'$addToSet': '$_id'},
                    "count": {"$sum": 1}
                }
            },
            {
                '$match': {
                    'count': {'$gt': 1}
                }
            },
            {
                '$sort': {
                    'count': -1
                }
            }
        ]).get('result')
        if targets:
            raise AssertionError(
                'Multiple {} records associated with nodes: {}. '
                'Use scripts.clean_invalid_addon_settings to fix this issue.'.format(
                    collection, ', '.join([each['_id'] for each in targets])
                )
            )


class Command(BaseCommand):
    help = 'Migrates data from tokumx to postgres'

    def add_arguments(self, parser):
        parser.add_argument('--nodelogs', action='store_true', help='Run nodelog migrations')
        parser.add_argument('--nodelogsguids', action='store_true', help='Run nodelog guid migrations')
        parser.add_argument('--profile', action='store', help='Filename to dump profiling information')
        parser.add_argument('--dependents', action='store_true', help='Migrate things that are dependent on other things.')

    def do_model(self, django_model, options):
        with ipdb.launch_ipdb_on_exception():
            if not options['nodelogsguids']:
                save_bare_models.delay(django_model)

    def handle(self, *args, **options):
        if options['profile']:
            profiler = Profile()
            profiler.runcall(self._handle, *args, **options)
            stats = pstats.Stats(profiler).sort_stats('cumulative')
            stats.print_stats()
            stats.dump_stats(options['profile'])
        else:
            self._handle(*args, **options)

    def _handle(self, *args, **options):
        # it's either this or catch the exception and put them in the blacklistguid table
        init_app(routes=False, attach_request_handlers=False, fixtures=False)
        set_backend()
        register_nonexistent_models_with_modm()

        if options['dependents']:
            make_guids()
            fix_guids()
            return

        models = get_ordered_models()
        # guids never, pls
        models.pop(models.index(Guid))

        if not options['nodelogs'] and not options['nodelogsguids']:
            ensure_no_duplicate_users()
        if not options['nodelogs']:
            logger.info('Removing duplicate addon node settings...')
            find_duplicate_addon_node_settings()
            logger.info('Removing duplicate addon user settings...')
            find_duplicate_addon_user_settings()
        for django_model in models:
            if not options['nodelogs'] and not options['nodelogsguids'] and django_model is NodeLog:
                continue
            elif (options['nodelogs'] or options['nodelogsguids']) and django_model is not NodeLog:
                continue
            elif django_model is AbstractNode:
                continue

            if not hasattr(django_model, 'modm_model_path'):
                logger.info('################################################\n'
                      '{}.{} doesn\'t have a modm_model_path\n'
                      '################################################'.format(
                    django_model._meta.model.__module__, django_model._meta.model.__name__,))
                continue
            self.do_model(django_model, options)

        # Handle system tags, they're on nodes, they need a special migration
        if not options['nodelogs'] and not options['nodelogsguids']:
            with ipdb.launch_ipdb_on_exception():
                save_bare_system_tags.delay()
                migrate_page_counters.delay()
                migrate_user_activity_counters.delay()
