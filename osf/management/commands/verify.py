from __future__ import unicode_literals

# import logging
import os
import sys
from datetime import datetime
from collections import deque
from itertools import izip_longest

import errno

import logging

import modularodm
import pytz
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import connection
from django.db.models import TextField, CharField
from pymongo.errors import OperationFailure

from api.base.celery import app
from osf.management.commands.migratedata import register_nonexistent_models_with_modm, get_modm_model
from osf.management.commands.migraterelations import build_toku_django_lookup_table_cache, format_lookup_key
from osf.models import BlackListGuid, NotificationSubscription, PrivateLink, Registration, Node, Collection
from osf.models import EmbargoTerminationApproval
from osf.models import OSFUser
from osf.models import Tag
from osf.utils.order_apps import get_ordered_models
from website.app import init_app
from website.files.models import StoredFileNode
from website.models import User as MUser, Node as MNode
from .migratedata import set_backend

# logger = logging.getLogger('migrations')
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

class NotGonnaDoItException(Exception):
    pass


class Command(BaseCommand):
    help = 'Validates migrations from tokumx to postgres'

    def handle(self, *args, **options):
        django_models = get_ordered_models()

        for django_model in django_models:
            if not hasattr(django_model, 'modm_model_path'):
                logger.info('################################################\n'
                      '{} doesn\'t have a modm_model_path\n'
                      '################################################'.format(
                    django_model._meta.model.__name__))
                continue
            elif django_model.__subclasses__() != []:
                logger.info('Skipping {}.{}'.format(django_model.__module__, django_model))
                continue
            elif django_model is Tag:
                validate_tags.delay()
            elif django_model is BlackListGuid:
                # TODO we'll do this by hand because tags are special
                # TODO we'll do blacklistguids by hand because they've got a bunch of new ones that don't exist in modm
                # TODO specifically, from register_none_existent_models
                continue
            do_model.delay(django_model)


def check_tags(postgres_row, mongo_obj, model_type):
    assert postgres_row[0] == mongo_obj['_id']

    mongo_obj['tags'] = set(mongo_obj.get('tags', []))
    mongo_obj['system_tags'] = set(mongo_obj.get('system_tags', []))
    postgres_row = (postgres_row[0], set(postgres_row[1]), set(postgres_row[2]))

    if postgres_row[1] != mongo_obj['tags']:
        logger.error(
            'Incorrect tags on %s %s. Difference: Postgres = %s Mongo = %s',
            model_type,
            postgres_row[0],
            postgres_row[1] - mongo_obj['tags'],
            mongo_obj['tags'] - postgres_row[1],
        )

    if postgres_row[2] != mongo_obj['system_tags'] and model_type != 'AbstractNode':
        logger.error(
            'Incorrect system_tags on %s %s. Difference: Postgres = %s Mongo = %s',
            model_type,
            postgres_row[0],
            postgres_row[2] - mongo_obj['system_tags'],
            mongo_obj['system_tags'] - postgres_row[2],
        )


def check_tags_cursors(postgres_cursor, mongo_cursor, model_type):
    p_backlog, m_backlog = deque(), deque()
    logger.info('Checking tags and system tags for %s', model_type)
    for postgres_row, mongo_obj in izip_longest(postgres_cursor, mongo_cursor):

        if postgres_row is not None:
            p_backlog.append(postgres_row)

        if mongo_obj is not None:
            m_backlog.append(mongo_obj)

        for i, row in enumerate(p_backlog):
            for j, obj in enumerate(m_backlog):
                if row[0] == obj['_id']:
                    break
            if row[0] == obj['_id']:
                break
        else:
            continue

        for _ in range(i):
            logger.warning('Found missing %s %s from Mongo', model_type, p_backlog.popleft()[0])

        for _ in range(j):
            logger.warning('Found missing %s %s from Postgres', model_type, m_backlog.popleft()['_id'])

        check_tags(p_backlog.popleft(), m_backlog.popleft(), model_type)

    for mongo_obj in m_backlog:
        logger.warning('Found missing %s %s from Postgres', model_type, mongo_obj['_id'])

    for postgres_row in p_backlog:
        logger.warning('Found missing %s %s from Mongo', model_type, postgres_row[0])


@app.task()
def validate_tags():
    from osf.models import AbstractNode
    from osf.models import BaseFileNode

    set_backend()
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    register_nonexistent_models_with_modm()

    for model in (OSFUser, AbstractNode, BaseFileNode):
        with connection.cursor() as cursor:
            if model is not BaseFileNode:
                cursor.execute('''SELECT
                    osf_guid._id
                    , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                        FROM "{through_table}"
                            JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                        WHERE "{through_table}"."{through_column}" = "{table}".id
                        AND osf_tag.system IS FALSE
                    ) AS tags
                    , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                        FROM "{through_table}"
                            JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                        WHERE "{through_table}"."{through_column}" = "{table}".id
                        AND osf_tag.system IS TRUE
                    ) AS system_tags
                    FROM "{table}"
                    JOIN osf_guid ON osf_guid.object_id = "{table}".id
                    JOIN django_content_type ON osf_guid.content_type_id = django_content_type.id
                    WHERE django_content_type.model = %s
                    ORDER BY osf_guid._id
                '''.format(
                    table=model._meta.db_table,
                    through_table=model._meta.get_field('tags').m2m_db_table(),
                    through_column=model._meta.get_field('tags').m2m_column_name(),
                ), [model._meta.model_name])

                modm_model = get_modm_model(model)
                mongo_cursor = modm_model._storage[0].db[modm_model._storage[0].collection].find({}, {'tags': 1, 'system_tags': 1}).sort('_id')

                check_tags_cursors(cursor, mongo_cursor, model.__name__)
                continue

            # Files are special
            cursor.execute('''SELECT
                _id
                , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                    FROM "{through_table}"
                        JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                    WHERE "{through_table}"."{through_column}" = "{table}".id
                    AND osf_tag.system IS FALSE
                ) AS tags
                , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                    FROM "{through_table}"
                        JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                    WHERE "{through_table}"."{through_column}" = "{table}".id
                    AND osf_tag.system IS TRUE
                ) AS system_tags
                FROM "{table}"
                WHERE type NOT IN ('osf.trashedfile', 'osf.trashedfolder')
                ORDER BY _id
            '''.format(
                table=model._meta.db_table,
                through_table=model._meta.get_field('tags').m2m_db_table(),
                through_column=model._meta.get_field('tags').m2m_column_name(),
            ), [model._meta.model_name])

            modm_model = get_modm_model(model)
            mongo_cursor = modm_model._storage[0].db[modm_model._storage[0].collection].find({}, {'tags': 1, 'system_tags': 1}).sort('_id')

            check_tags_cursors(cursor, mongo_cursor, model.__name__)

            # Files are special
            cursor.execute('''SELECT
                _id
                , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                    FROM "{through_table}"
                        JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                    WHERE "{through_table}"."{through_column}" = "{table}".id
                    AND osf_tag.system IS FALSE
                ) AS tags
                , (SELECT COALESCE(array_agg(osf_tag.name), ARRAY[]::text[])
                    FROM "{through_table}"
                        JOIN osf_tag ON "{through_table}".tag_id = osf_tag.id
                    WHERE "{through_table}"."{through_column}" = "{table}".id
                    AND osf_tag.system IS TRUE
                ) AS system_tags
                FROM "{table}"
                WHERE type IN ('osf.trashedfile', 'osf.trashedfolder')
                ORDER BY _id
            '''.format(
                table=model._meta.db_table,
                through_table=model._meta.get_field('tags').m2m_db_table(),
                through_column=model._meta.get_field('tags').m2m_column_name(),
            ), [model._meta.model_name])

            from website.models import TrashedFileNode
            modm_model = TrashedFileNode
            mongo_cursor = modm_model._storage[0].db[modm_model._storage[0].collection].find({}, {'tags': 1, 'system_tags': 1}).sort('_id')

            check_tags_cursors(cursor, mongo_cursor, 'TrashedFileNode')


@app.task()
def do_model(django_model):
    set_backend()
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    register_nonexistent_models_with_modm()

    page_size = django_model.migration_page_size

    validate_model_data(django_model, page_size=page_size)


def validate_m2m_field(field_name, django_obj, modm_obj):
    try:
        field = getattr(django_obj, field_name)

        # handle both forward and reverse rels
        if hasattr(django_obj, field_name):
            manager = field
            # skip groups and permissions
            if manager.model is Group or manager.model is Permission:
                return
            primary_identifier_name = manager.model.primary_identifier_name
        else:
            manager_name = '{}_set'.format(field.through._meta.object_name).lower()
            manager = getattr(django_obj, manager_name)
            try:
                primary_identifier_name = field.through._meta.model.primary_identifier_name
            except AttributeError:
                primary_identifier_name = '_id'
        django_guids = manager.all().values_list(primary_identifier_name, flat=True)

        flat_django_guids = []

        for guid in django_guids:
            if isinstance(guid, list):
                flat_django_guids.extend(guid)
            else:
                flat_django_guids.append(guid)

        django_guids = flat_django_guids

        # if there's a field alias, let's use that.
        if getattr(django_obj, 'FIELD_ALIASES', None) is None:
            modm_field_name = field_name
        else:
            modm_field_name = {v: k for k, v in getattr(django_obj, 'FIELD_ALIASES', {}).iteritems()}.get(field_name, field_name)

        if modm_field_name not in modm_obj.to_storage():
            logger.error('{} was not in {} for {}.{} with id {}'.format(modm_field_name, modm_obj.to_storage(), django_obj._meta.model.__module__, django_obj._meta.model.__name__, django_obj._id))
            return
        modm_guids = modm_obj.to_storage()[modm_field_name]
        for django_guid in django_guids:
            if isinstance(django_guid, list):
                for djg in django_guid:
                    try:
                        assert djg in modm_guids, '{} for model {}.{} with id {} was not in modm guids for field {}'.format(django_guid, django_obj._meta.model.__module__, django_obj._meta.model.__name__, django_obj._id, modm_field_name)
                    except AssertionError as ex:
                        logger.error(ex)
            else:
                try:
                    assert django_guid in modm_guids, '{} for model {}.{} with id {} was not in modm guids for field {}'.format(django_guid, django_obj._meta.model.__module__, django_obj._meta.model.__name__, django_obj._id, modm_field_name)
                except AssertionError as ex:
                    logger.error(ex)
    except AttributeError as ex:
        logger.warning('AttributeError on model {}.{} for id {} and field_name {}'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name))
        return


def validate_fk_relation(field_name, django_obj, modm_obj):
    try:
        if field_name in ['content_type', 'content_type_pk', 'content_type_id']:
            # modm doesn't have gfk
            return

        if isinstance(modm_obj, StoredFileNode) and field_name == 'deleted_by':
            return

        if django_obj._meta.model is EmbargoTerminationApproval and field_name == 'initiated_by':
            # EmbargoTerminationApproval didn't have an initiated_by in modm even though it was supposed to.
            return

        django_field_value = getattr(django_obj, field_name)
        # if there's a field alias, let's use that.
        if getattr(django_obj, 'FIELD_ALIASES', None) is None:
            modm_field_name = field_name
        else:
            modm_field_name = {v: k for k, v in getattr(django_obj, 'FIELD_ALIASES', {}).iteritems()}.get(field_name, field_name)


        if django_obj._meta.model is NotificationSubscription:
            modm_field_name = 'owner'
            modm_field_value = getattr(modm_obj, modm_field_name)

            if isinstance(modm_field_value, MUser):
                django_field_value = getattr(django_obj, 'user')
            elif isinstance(modm_field_value, MNode):
                django_field_value = getattr(django_obj, 'node')

        else:
            modm_field_value = getattr(modm_obj, modm_field_name)

        if modm_field_value and django_field_value:
            try:
                assert modm_field_value._id == django_field_value._id, 'Modm field {} of obj {}:{} with value of {} doesn\'t equal django field with value {}'.format(field_name, type(modm_obj), modm_obj._id, modm_field_value._id, django_field_value._id)
            except AssertionError as ex:
                logger.error(ex)
        elif modm_field_value is not None and django_field_value is None:
            logger.error('{} of {!r} was None in django {} but {!r} in modm'.format(field_name, modm_obj, django_obj._id, modm_field_value))
    except AttributeError as ex:
        logger.warning('AttributeError on model {}.{} for id {} and field_name {}'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name))
        return

def validate_basic_field(field_name, django_obj, modm_obj):
    try:
        if field_name in ['id', 'pk', 'object_id', 'guid_string', 'last_login', 'is_superuser', 'content_type_pk', 'content_type_id', 'type', 'piwik_site_id']:
            # modm doesn't have these
            return

        # if there's a field alias, let's use that.
        if getattr(django_obj, 'FIELD_ALIASES', None) is None:
            modm_field_name = field_name
        else:
            modm_field_name = {v: k for k, v in getattr(django_obj, 'FIELD_ALIASES', {}).iteritems()}.get(field_name, field_name)


        if field_name == '_history':
            modm_field_name = 'history'

        if field_name == '_path':
            modm_field_name = 'path'

        if field_name == '_materialized_path':
            modm_field_name = 'materialized_path'

        if isinstance(modm_obj, StoredFileNode) and field_name == 'deleted_on':
            return

        if modm_field_name is False:
            return

        modm_value = getattr(modm_obj, modm_field_name)
        django_value = getattr(django_obj, field_name)

        if django_value is None and modm_value is None:
            return

        # we will never have to do this again
        if modm_value == 'JyZND':
            modm_value = modm_value.lower()


        if field_name == 'password':
            modm_value = 'bcrypt${}'.format(modm_value)

        if type(django_value) != type(modm_value):

            if isinstance(modm_value, modularodm.fields.lists.List):
                modm_value = list(modm_value)

            # jsonb fields
            if modm_value is None and django_value == {}:
                return

            # bool defaulting to False but None in modm is falsey
            if modm_value is None and django_value is False:
                return

            # sometimes None is an empty string because MongoDB
            if modm_value is None and django_value == '':
                return

            if isinstance(django_obj._meta.get_field_by_name(field_name), (CharField, TextField)) and django_obj._meta.get_field_by_name(field_name).max_length == len(django_value) and django_value != modm_value:
                logger.warn('{} on model {}.{} with id {} did not match modm but was field max_length'.format(field_name, django_obj._meta.model.__module__, django_obj._meta.model.__class__, django_obj._id))

            if modm_value is None:
                logger.error('modm value was None but django value was {} for {} on {}.{} with ID of {}'.format(django_value, field_name, django_obj._meta.model.__module__, django_obj._meta.model.__class__, getattr(django_obj, getattr(django_obj, '_primary_identifier_name', ''), None)))
                return

            # sometimes strings used to be integers, in some documents... LicenseRecord.year
            try:
                assert django_value.__class__(modm_value) == django_value, 'WITH TYPECAST: {}.{} _id:{} django_field_name:{} django_value:{} modm_field_name:{} modm_value:{!r}'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name, django_value, modm_field_name, modm_value)
            except AssertionError as ex:
                logger.error(ex)
            return

        if isinstance(modm_value, datetime):
            try:
                assert django_value.tzinfo is not None and django_value.tzinfo.utcoffset(django_value) is not None, 'Django datetime is naive for field {} on model {}.{} with id {}'.format(field_name, django_obj._meta.model.__module__, django_obj._meta.model.__class__, django_obj._id)
            except AssertionError as ex:
                logger.error(ex)

            try:
                assert django_value == pytz.utc.localize(modm_value), '{}.{} _id:{} django_field_name:{} django_value:{} modm_field_name:{} modm_value:{}'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name, django_value, modm_field_name, pytz.utc.localize(modm_value))
            except AssertionError as ex:
                logger.error(ex)
            return
        try:
            assert django_value == modm_value, '{}.{} _id:{} django_field_name{} django_value:{} modm_field_name:{} modm_value:{!r}'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name, django_value, modm_field_name, modm_value)
        except AssertionError as ex:
            logger.error(ex)
    except AttributeError as ex:
        logger.warning('AttributeError on model {}.{} for id {} and field_name {}\n'.format(django_obj.__module__, django_obj.__class__, django_obj._id, field_name, ex))
        return


def get_pk(modm_object, django_model, modm_to_django):
    try:
        return modm_to_django[format_lookup_key(modm_object._id, model=django_model)]
    except KeyError as ex:
        logger.error('modm key {} not found in lookup table {}'.format(
            format_lookup_key(modm_object._id, ContentType.objects.get_for_model(django_model).pk), ex))


def mkdir_p(path):
    """http://stackoverflow.com/a/600612/190597 (tzot)"""
    try:
        os.makedirs(path, exist_ok=True)  # Python>3.2
    except TypeError:
        try:
            os.makedirs(path)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else: raise


class MkdirPFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='w+', encoding=None, delay=0):
        mkdir_p(os.path.dirname(filename))
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

@app.task(bind=True, max_retries=None)  # retry forever because of cursor timeouts
def validate_page_of_model_data(self, django_model, basic_fields, fk_relations, m2m_relations, offset, limit):
    logger = get_task_logger(__name__)

    logger.level = logging.WARNING

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    hndlr = MkdirPFileHandler('../logs/{}.{}/{}.log'.format(django_model._meta.model.__module__, django_model._meta.model.__name__, self.request.id), mode='w')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    hndlr.setFormatter(formatter)
    logger.addHandler(hndlr)

    try:
        set_backend()
        init_app(routes=False, attach_request_handlers=False, fixtures=False)
        register_nonexistent_models_with_modm()

        modm_model = get_modm_model(django_model)
        modm_to_django = build_toku_django_lookup_table_cache()

        if isinstance(django_model.modm_query, dict):
            modm_queryset = modm_model.find(**django_model.modm_query)
        else:
            modm_queryset = modm_model.find(django_model.modm_query)
        count = 0
        page_of_modm_objects = modm_queryset.sort('_id')[offset:limit]
        django_ids = [get_pk(modm_obj, django_model, modm_to_django) for modm_obj in page_of_modm_objects]
        django_objects = django_model.objects.filter(id__in=django_ids)

        # TODO users aren't going to match
        if django_model is not OSFUser:
            try:
                assert len(django_ids) == len(django_objects) == len(page_of_modm_objects), 'Lost some keys along the way for {}.{}\n' \
                                                                                        'Django_id count: {}\n' \
                                                                                        'Django count: {}\n' \
                                                                                        'Modm count: {}'.format(
                    django_model._meta.model.__module__,
                    django_model._meta.model.__name__,
                    len(django_ids),
                    len(django_objects),
                    len(page_of_modm_objects),
                )
            except AssertionError as ex:
                logger.error(ex)
                modm_keys = set(page_of_modm_objects.get_keys())
                try:
                    primary_identifier_name = django_model._meta.model.primary_identifier_name
                except AttributeError:
                    primary_identifier_name = '_id'
                django_keys = set(django_objects.values_list(primary_identifier_name, flat=True))
                missing = modm_keys - django_keys
                logger.error('Missing Keys: {}'.format(missing))

        for modm_obj in page_of_modm_objects:
            try:
                django_obj = django_objects.get(pk=get_pk(modm_obj, django_model, modm_to_django))
            except ObjectDoesNotExist:
                logger.error('Django object {} with id {} does not exist'.format(django_model, modm_obj._id))
                continue
            for m2m_field in m2m_relations:
                validate_m2m_field(m2m_field.name, django_obj, modm_obj)
            for fk_field in fk_relations:
                validate_fk_relation(fk_field.name, django_obj, modm_obj)
            for basic_field in basic_fields:
                validate_basic_field(basic_field.name, django_obj, modm_obj)

            count += 1
        logger.info('Through {} {}.{}s...'.format(count, django_model._meta.model.__module__, django_model._meta.model.__name__))
    except OperationFailure as ex:
        logger.error(
            'Retrying: Failed to validate page model: {} offset:{} limit:{} of foreign keys with exception {}'.format(
                django_model, offset, limit, ex))
        logger.error('{} {}'.format(ex.__dict__, ex.__class__))
        self.retry(countdown=20)  # retry in 20s

    hndlr.flush()
    if os.stat(hndlr.baseFilename).st_size == 0:
        os.remove(hndlr.baseFilename)


def validate_model_data(django_model, page_size=20000):
    logger.info('Starting {} on {}...'.format(
        sys._getframe().f_code.co_name, django_model._meta.model.__name__))
    count = 0
    modm_model = get_modm_model(django_model)
    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)

    total = modm_queryset.count()

    m2m_relations = [field for field in
                     django_model._meta.get_fields() if
                     field.is_relation and field.many_to_many and not hasattr(field, 'field')]

    fk_relations = [field for field in django_model._meta.get_fields() if
                    field.is_relation and not field.auto_created and (field.many_to_one or field.one_to_one)]

    basic_fields = [field for field in django_model._meta.get_fields() if not field.is_relation]

    while count < total:
        offset = count
        limit = (count + page_size) if (count + page_size) < total else total
        validate_page_of_model_data.delay(django_model, basic_fields, fk_relations, m2m_relations, offset, limit)
        count += page_size
