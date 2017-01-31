from __future__ import unicode_literals

import gc
import importlib
import sys

import itertools
from box import BoxClient
from box import BoxClientException
from bson import ObjectId
from dropbox.client import DropboxClient
from dropbox.rest import ErrorResponse
from github3 import GitHubError
from oauthlib.oauth2 import InvalidGrantError

from addons.base.models import BaseOAuthNodeSettings
from framework import encryption
from osf.models import ExternalAccount
from osf.models import OSFUser
from addons.s3 import utils


import ipdb
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from framework.auth.core import User as MODMUser
from framework.mongo import database
from framework.transactions.context import transaction as modm_transaction
from modularodm import Q as MQ
from osf.models import NodeLog, PageCounter, Tag, UserActivityCounter
from osf.models.base import Guid, GuidMixin, OptionalGuidMixin
from osf.models.node import AbstractNode
from osf.utils.order_apps import get_ordered_models
from psycopg2._psycopg import AsIs
from scripts.register_oauth_scopes import set_backend
from typedmodels.models import TypedModel

from addons.github.api import GitHubClient
from website.files.models import StoredFileNode as MODMStoredFileNode
from website.models import Guid as MODMGuid
from website.models import Node as MODMNode
import logging

logger = logging.getLogger(__name__)

encryption.encrypt = lambda x: x
encryption.decrypt = lambda x: x

def get_modm_model(django_model):
    module_path, model_name = django_model.modm_model_path.rsplit('.', 1)
    modm_module = importlib.import_module(module_path)
    return getattr(modm_module, model_name)


def migrate_page_counters(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
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
                    print('Saving {} {} through {}...'.format(PageCounter._meta.model.__name__, start, count))

                    saved_django_objects = PageCounter.objects.bulk_create(django_objects)

                    print('Done with {} {} in {} seconds...'.format(len(saved_django_objects), PageCounter._meta.model.__name__, (timezone.now()-page_finish_time).total_seconds()))
                    saved_django_objects = []
                    print('Took out {} trashes'.format(gc.collect()))
    total = None
    count = None
    print('Took out {} trashes'.format(gc.collect()))
    print('Finished {} in {} seconds...'.format(sys._getframe().f_code.co_name, (timezone.now()-start_time).total_seconds()))


def migrate_user_activity_counters(page_size=20000):
    print('Starting {}...'.format(sys._getframe().f_code.co_name))
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
                    print('Saving {} {} through {}...'.format(UserActivityCounter._meta.model.__name__, start, count))

                    saved_django_objects = UserActivityCounter.objects.bulk_create(django_objects)

                    print('Done with {} {} in {} seconds...'.format(len(saved_django_objects), UserActivityCounter._meta.model.__name__, (timezone.now()-page_finish_time).total_seconds()))
                    saved_django_objects = []
                    print('Took out {} trashes'.format(gc.collect()))
    total = None
    count = None
    print('Took out {} trashes'.format(gc.collect()))
    print('Finished {} in {} seconds...'.format(sys._getframe().f_code.co_name, (timezone.now()-start_time).total_seconds()))


def make_guids():
    print('Starting {}...'.format(sys._getframe().f_code.co_name))

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
                    print('Making guids for {}'.format(model._meta.model.__name__))
                    try:
                        cursor.execute(sql)
                    except IntegrityError as ex:
                        ipdb.set_trace()



            guids = MODMGuid.find()
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
            print('{} MODM Guids, {} Orphaned Guids, {} Guids to Make, {} Existing guids'.format(len(guid_keys), len(orphaned_guids), len(guids_to_make), len(existing_guids)))
            from django.apps import apps
            model_names = {m._meta.model.__name__.lower(): m._meta.model for m in apps.get_models()}

            with ipdb.launch_ipdb_on_exception():
                # loop through missing guids
                for guid in guids_to_make:
                    # load them from modm
                    guid_dict = MODMGuid.load(guid).to_storage()
                    # if they don't have a referent toss them
                    if guid_dict['referent'] is None:
                        print('{} has no referent.'.format(guid))
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
                        print('Couldn\'t find model for {}'.format(modm_model_string))
                        continue
                    # get the id from the to_storage dictionary
                    modm_model_id = guid_dict['_id']
                    # if it's something that should have a guid
                    if issubclass(referent_model, GuidMixin) or issubclass(referent_model, OptionalGuidMixin):
                        try:
                            # find it's referent
                            referent_instance = referent_model.objects.get(guid_string__contains=[modm_model_id.lower()])
                        except referent_model.DoesNotExist:
                            print('Couldn\'t find referent for {}:{}'.format(referent_model._meta.model.__name__, modm_model_id))
                            continue
                    else:
                        # we shouldn't ever get here, bad data
                        print('Found guid pointing at {} type, dropping it on the floor.'.format(modm_model_string))
                        continue

                    # if we got a referent instance create the guid
                    if referent_instance:
                        Guid.objects.create(referent=referent_instance)
                    else:
                        print('{} {} didn\'t create a Guid'.format(referent_model._meta.model.__name__, modm_model_id))

            print('Started creating blacklist orphaned guids.')
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO
                      osf_blacklistguid
                      (guid)
                    VALUES %(guids)s ON CONFLICT DO NOTHING;
                """
                params = ''.join(['(\'{}\'), '.format(og) for og in orphaned_guids])[0:-2]
                cursor.execute(sql, {'guids': AsIs(params)})


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
                    if (count - page_size) < 0:
                        start = 0
                    else:
                        start = count - page_size
                    print(
                        'Saving {} {} through {}...'.format(django_model._meta.model.__name__,
                                                            start,
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


class DuplicateExternalAccounts(Exception):
    pass


def save_bare_external_accounts(page_size=100000):
    from website.models import ExternalAccount as MODMExternalAccount

    def validate_box(external_account):
        client = BoxClient(external_account.oauth_key)
        try:
            client.get_user_info()
        except (BoxClientException, IndexError):
            return False
        return True

    def validate_dropbox(external_account):
        client = DropboxClient(external_account.oauth_key)
        try:
            client.account_info()
        except (ValueError, IndexError, ErrorResponse):
            return False
        return True

    def validate_github(external_account):
        client = GitHubClient(external_account=external_account)
        try:
            client.user()
        except (GitHubError, IndexError):
            return False
        return True

    def validate_googledrive(external_account):
        try:
            external_account.node_settings.fetch_access_token()
        except (InvalidGrantError, AttributeError):
            return False
        return True

    def validate_s3(external_account):
        if utils.can_list(external_account.oauth_key, external_account.oauth_secret):
            return True
        return False

    account_validators = dict(
        box=validate_box,
        dropbox=validate_dropbox,
        github=validate_github,
        googledrive=validate_googledrive,
        s3=validate_s3
    )

    django_model_classes_with_fk_to_external_account = BaseOAuthNodeSettings.__subclasses__()
    django_model_classes_with_m2m_to_external_account = [OSFUser]


    print('Starting save_bare_external_accounts...')
    start = timezone.now()

    external_accounts = MODMExternalAccount.find()
    accounts_by_provider = dict()

    for ea in external_accounts:
        provider_tuple = (ea.provider, str(ea.provider_id))
        if provider_tuple in accounts_by_provider.keys():
            accounts_by_provider[provider_tuple].append(ea)
        else:
            accounts_by_provider[provider_tuple] = [ea, ]

    bad_accounts = {k:v for k, v in accounts_by_provider.iteritems() if len(v) > 1}
    good_accounts = [v[0] for k, v in accounts_by_provider.iteritems() if len(v) == 1]

    for (provider, provider_id), providers_accounts in bad_accounts.iteritems():
        good_provider_accounts = []
        for modm_external_acct in providers_accounts:
            if account_validators[provider](modm_external_acct):
                logger.info('Account {} checks out as valid.'.format(modm_external_acct))
                good_provider_accounts.append(modm_external_acct)
        if len(good_provider_accounts) > 1:
            raise DuplicateExternalAccounts('{} {} had {} good accounts.'.format(provider, provider_id, len(good_provider_accounts)))
        else:
            itertools.chain(good_accounts, good_provider_accounts)

    with transaction.atomic():
        good_django_accounts = ExternalAccount.objects.bulk_create([ExternalAccount.migrate_from_modm(x) for x in good_accounts])

        external_account_mapping = dict(ExternalAccount.objects.all().values_list('_id', 'id'))

        for (provider, provider_id), providers_accounts in bad_accounts.iteritems():
            newest_modm_external_account_id = str(ObjectId.from_datetime(timezone.datetime(1970, 1, 1, tzinfo=timezone.UTC())))
            modm_external_account_ids_to_replace = []
            for modm_external_acct in providers_accounts:
                if ObjectId(modm_external_acct._id).generation_time > ObjectId(newest_modm_external_account_id).generation_time:
                    modm_external_account_ids_to_replace.append(newest_modm_external_account_id)
                    newest_modm_external_account_id = modm_external_acct._id

            ext = ExternalAccount.migrate_from_modm(MODMExternalAccount.load(newest_modm_external_account_id))
            ext.save()
            external_account_mapping[newest_modm_external_account_id] = ext.id

            for modm_external_account_to_replace in modm_external_account_ids_to_replace:
                for django_model_class in django_model_classes_with_fk_to_external_account:
                    if hasattr(django_model_class, 'modm_model_path'):
                        modm_model_class = get_modm_model(django_model_class)
                        matching_models = modm_model_class.find(MQ('external_account', 'eq', modm_external_account_to_replace))
                        django_model_class.objects.filter(_id__in=matching_models.get_keys()).update(external_account_id=external_account_mapping[newest_modm_external_account_id])

                for django_model_class in django_model_classes_with_m2m_to_external_account:
                    if hasattr(django_model_class, 'modm_model_path'):
                        modm_model_class = get_modm_model(django_model_class)
                        for model_guid in modm_model_class.find(MQ('external_accounts', 'eq', modm_external_account_to_replace)).get_keys():
                            django_model = django_model_class.objects.get(guids___id=model_guid)
                            django_model.external_accounts.add(external_account_mapping[newest_modm_external_account_id])


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
    threads = 5

    def add_arguments(self, parser):
        parser.add_argument('--nodelogs', action='store_true', help='Run nodelog migrations')
        parser.add_argument('--nodelogsguids', action='store_true', help='Run nodelog guid migrations')

    def handle(self, *args, **options):
        set_backend()
        # it's either this or catch the exception and put them in the blacklistguid table
        register_nonexistent_models_with_modm()

        models = get_ordered_models()
        # guids never, pls
        models.pop(models.index(Guid))
        models.pop(models.index(ExternalAccount))

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
            modm_model = get_modm_model(django_model)
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
            with ipdb.launch_ipdb_on_exception():
                save_bare_system_tags()
                make_guids()
                save_bare_external_accounts()
                migrate_page_counters()
                migrate_user_activity_counters()
