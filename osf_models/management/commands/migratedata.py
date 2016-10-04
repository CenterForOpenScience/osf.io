import gc
import importlib
import sys

import ipdb
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import IntegrityError
from django.db import connection
from django.db import transaction
from django.utils import timezone
from framework.auth.core import User as MODMUser
from framework.transactions.context import transaction as modm_transaction
from modularodm import Q as MQ
from osf_models.models import NodeLog
from osf_models.models import Tag
from osf_models.models.base import GuidMixin, Guid, OptionalGuidMixin, BlackListGuid
from osf_models.models.node import AbstractNode
from osf_models.utils.order_apps import get_ordered_models
from typedmodels.models import TypedModel
from website.files.models import StoredFileNode as MODMStoredFileNode
from website.models import Node as MODMNode
from website.models import Guid as MODMGuid


def make_guids():
    import ipdb
    print('Starting {}...'.format(sys._getframe().f_code.co_name))

    guid_models = [model for model in get_ordered_models() if (issubclass(model, GuidMixin) or issubclass(model, OptionalGuidMixin)) and (not issubclass(model, AbstractNode) or model is AbstractNode)]

    with connection.cursor() as cursor:
        with transaction.atomic():
            for model in guid_models:
                with transaction.atomic():
                    content_type = ContentType.objects.get_for_model(model)
                    if issubclass(model, TypedModel):
                        sql = """
                                INSERT INTO osf_models_guid
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
                                INSERT INTO osf_models_guid
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
                    print('Making guids for {}'.format(model._meta.model.__name__))
                    try:
                        cursor.execute(sql)
                    except IntegrityError as ex:
                        import ipdb
                        ipdb.set_trace()

            guids = MODMGuid.find()
            guid_keys = MODMGuid.find().get_keys()
            orphaned_guids = [g._id for g in guids if g.to_storage()['referent'][1] in ['dropboxfile', 'osfstorageguidfile', 'osfguidfile', 'githubguidfile', 'nodefile', 'boxfile', 'figshareguidfile', 's3guidfile', 'dataversefile']]
            existing_guids = Guid.objects.all().values_list('_id', flat=True)
            guids_to_make = set(guid_keys) - set(orphaned_guids) - set(existing_guids)
            print('{} MODM Guids, {} Orphaned Guids, {} Guids to Make, {} Existing guids'.format(len(guid_keys), len(orphaned_guids), len(guids_to_make), len(existing_guids)))
            from django.apps import apps
            model_names = {m._meta.model.__name__.lower(): m._meta.model for m in apps.get_models()}

            with ipdb.launch_ipdb_on_exception():
                for guid in guids_to_make:
                    guid_dict = MODMGuid.load(guid).to_storage()
                    modm_model_string = guid_dict['referent'][1]
                    if modm_model_string == 'user':
                        modm_model_string = 'osfuser'
                    referent_model = model_names[modm_model_string]
                    modm_model_id = guid_dict['_id']
                    if issubclass(referent_model, GuidMixin) or issubclass(referent_model, OptionalGuidMixin):
                        try:
                            referent_instance = referent_model.objects.get(guid_string__contains=[modm_model_id.lower()])
                        except referent_model.DoesNotExist:
                            print('Couldn\'t find Guid for {}:{}'.format(referent_model._meta.model.__name__, modm_model_id))
                            continue
                    else:
                        referent_instance = referent_model.objects.get(_id__iexact=modm_model_id)

                    if referent_instance:
                        Guid.objects.create(referent=referent_instance)
                    else:
                        print('{} {} didn\'t create a Guid'.format(referent_model._meta.model.__name__, modm_model_id))

            orphaned_guids = set(MODMGuid.find().get_keys()) - set(
                Guid.objects.all().values_list('_id', flat=True))
            guids_to_blacklist = []
            for guid in orphaned_guids:
                if not BlackListGuid.objects.filter(guid__iexact=guid).exists():
                    guids_to_blacklist.append(BlackListGuid(guid=guid))
                else:
                    print('BlackListGuid {} already exists...'.format(guid))
            print('Saving {} BlackListGuids'.format(len(guids_to_blacklist)))
            results = BlackListGuid.objects.bulk_create(guids_to_blacklist)

            print('Created {} BlackListGuids from orphaned Guids'.format(len(results)))


def save_bare_models(modm_queryset, django_model, page_size=20000):
    print('Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__name__))
    count = 0
    total = modm_queryset.count()
    hashes = set()

    while count < total:
        with transaction.atomic():
            django_objects = list()

            offset = count
            limit = (count + page_size) if (count + page_size) < total else total

            page_of_modm_objects = modm_queryset.sort('-_id')[offset:limit]

            if not hasattr(django_model, '_natural_key'):
                print('{} is missing a natural key!'.format(django_model._meta.model.__name__))

            for modm_obj in page_of_modm_objects:
                django_instance = django_model.migrate_from_modm(modm_obj)
                if django_instance is None:
                    count += 1
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
                            print('{} with guids {} was already in hashes'.format(django_instance._meta.model.__name__, found))
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
                if count % page_size == 0 or count == total:
                    page_finish_time = timezone.now()
                    print(
                        'Saving {} {} through {}...'.format(django_model._meta.model.__name__,
                                                            count - page_size,
                                                            count))
                    saved_django_objects = django_model.objects.bulk_create(django_objects)

                    print('Done with {} {} in {} seconds...'.format(len(saved_django_objects),
                                                                    django_model._meta.model.__name__, (
                                                                        timezone.now() -
                                                                        page_finish_time).total_seconds()))
                    modm_obj._cache.clear()
                    modm_obj._object_cache.clear()
                    saved_django_objects = []
                    page_of_modm_objects = []
                    print('Took out {} trashes'.format(gc.collect()))
    total = None
    count = None
    hashes = None
    print('Took out {} trashes'.format(gc.collect()))


def save_bare_system_tags(page_size=10000):
    print('Starting save_bare_system_tags...')
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

    created_system_tags = Tag.objects.bulk_create(system_tags)

    print('MODM System Tags: {}'.format(total))
    print('django system tags: {}'.format(Tag.objects.filter(system=True).count()))
    print('Done with {} in {} seconds...'.format(
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
def merge_duplicate_users():
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
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
        (timezone.now() - start).total_seconds()))


class Command(BaseCommand):
    help = 'Migrates data from tokumx to postgres'

    def add_arguments(self, parser):
        parser.add_argument('--nodelogs', action='store_true', help='Run nodelog migrations')
        parser.add_argument('--nodelogsguids', action='store_true', help='Run nodelog guid migrations')

    def handle(self, *args, **options):
        # TODO Handle contributors, they're not a direct 1-to-1 they'll need some love

        # it's either this or catch the exception and put them in the blacklistguid table
        register_nonexistent_models_with_modm()

        models = get_ordered_models()
        # guids never, pls
        models.pop(models.index(Guid))

        if not options['nodelogs'] and not options['nodelogsguids']:
            merge_duplicate_users()
            # merged users get blank usernames, running it twice fixes it.
            merge_duplicate_users()

        for django_model in models:
            if not options['nodelogs'] and not options['nodelogsguids'] and django_model is NodeLog:
                continue
            elif (options['nodelogs'] or options['nodelogsguids']) and django_model is not NodeLog:
                continue
            elif django_model is AbstractNode:
                continue

            if not hasattr(django_model, 'modm_model_path'):
                print('################################################\n'
                      '{} doesn\'t have a modm_model_path\n'
                      '################################################'.format(
                    django_model._meta.model.__name__))
                continue
            module_path, model_name = django_model.modm_model_path.rsplit('.', 1)
            modm_module = importlib.import_module(module_path)
            modm_model = getattr(modm_module, model_name)
            if isinstance(django_model.modm_query, dict):
                modm_queryset = modm_model.find(**django_model.modm_query)
            else:
                modm_queryset = modm_model.find(django_model.modm_query)

            with ipdb.launch_ipdb_on_exception():
                if not options['nodelogsguids']:
                    save_bare_models(modm_queryset, django_model,
                                     page_size=django_model.migration_page_size)
            modm_model._cache.clear()
            modm_model._object_cache.clear()
            print('Took out {} trashes'.format(gc.collect()))

        # Handle system tags, they're on nodes, they need a special migration
        if not options['nodelogs'] and not options['nodelogsguids']:
            save_bare_system_tags()
            make_guids()
