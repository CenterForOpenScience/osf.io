from __future__ import unicode_literals

import importlib

import gc
import ipdb
import sys

from datetime import datetime

import multiprocessing
import pytz
from django.core.management import BaseCommand
from gevent.threadpool import ThreadPool

from api.base.celery import app
from osf.management.commands.migratedata import register_nonexistent_models_with_modm, get_modm_model
from osf.management.commands.migraterelations import build_toku_django_lookup_table_cache, format_lookup_key
from osf.models import BlackListGuid
from osf.models import OSFUser
from osf.models import Tag
from osf.utils.order_apps import get_ordered_models
from website.app import init_app
from .migratedata import set_backend
import logging
logger = logging.getLogger('migrations')

class NotGonnaDoItException(BaseException):
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
            elif django_model is Tag or django_model is BlackListGuid:
                # we'll do this by hand because tags are special
                # we'll do blacklistguids by hand because they've got a bunch of new ones that don't exist in modm
                # specifically, from register_none_existent_models
                continue
            do_model.delay(django_model)


@app.task()
def do_model(django_model):
    set_backend()
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    register_nonexistent_models_with_modm()

    page_size = django_model.migration_page_size
    page_size = 10000

    validate_model_data(django_model, page_size=page_size)


def validate_m2m_field(field_name, django_obj, modm_obj):
    field = getattr(django_obj, field_name)

    # handle both forward and reverse rels
    if hasattr(django_obj, field_name):
        manager = field
        primary_identifier_name = manager.model.primary_identifier_name
    else:
        manager_name = '{}_set'.format(field.through._meta.object_name).lower()
        manager = getattr(django_obj, manager_name)
        try:
            primary_identifier_name = field.through._meta.model.primary_identifier_name
        except AttributeError:
            primary_identifier_name = '_id'
    django_guids = manager.all().values(primary_identifier_name)
    for django_guid in django_guids:
        assert django_guid in getattr(modm_obj, field_name).get_keys()


def validate_fk_relation(field_name, django_obj, modm_obj):
    if field_name in ['content_type', 'content_type_id']:
        # modm doesn't have gfk
        return
    django_field_value = getattr(django_obj, field_name)
    modm_field_value = getattr(modm_obj, field_name)
    if modm_field_value and django_field_value:
        assert modm_field_value._id == django_field_value._id
    elif modm_field_value is not None and django_field_value is None:
        logger.info('{} of {!r} was None in django but {} in modm'.format(field_name, modm_obj, django_obj, modm_field_value))
    else:
        logger.info('{} of {!r} were None'.format(field_name, modm_obj))


def validate_basic_field(field_name, django_obj, modm_obj):
    if field_name in ['id', 'pk', 'object_id']:
        # modm doesn't have ids
        return
    # if there's a field alias, let's use that.
    if getattr(django_obj, 'FIELD_ALIASES', None) is None:
        modm_field_name = field_name
    else:
        modm_field_name = {v: k for k, v in getattr(django_obj, 'FIELD_ALIASES', {}).iteritems()}.get(field_name, None)

    if modm_field_name is None:
        modm_field_name = field_name

    if modm_field_name is False:
        return
    if isinstance(getattr(modm_obj, modm_field_name), datetime):
        assert getattr(django_obj, field_name) == pytz.utc.localize(getattr(modm_obj, modm_field_name))
        return
    assert getattr(django_obj, field_name) == getattr(modm_obj, modm_field_name)


def get_pk(modm_object, django_model, modm_to_django):
    return modm_to_django[format_lookup_key(modm_object._id, model=django_model)]


@app.task()
def validate_page_of_model_data(django_model, basic_fields, fk_relations, m2m_relations, offset, limit):
    modm_model = get_modm_model(django_model)
    modm_to_django = build_toku_django_lookup_table_cache()

    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)
    count = 0
    page_of_modm_objects = modm_queryset.sort('-_id')[offset:limit]
    django_ids = [get_pk(modm_obj, django_model, modm_to_django) for modm_obj in page_of_modm_objects]
    django_objects = django_model.objects.filter(id__in=django_ids)

    # TODO users aren't going to match
    if django_model is not OSFUser:
        assert len(django_ids) == len(django_objects) == len(page_of_modm_objects), 'Lost some keys along the way for {}\n' \
                                                                                    'Django_id count: {}\n' \
                                                                                    'Django count: {}\n' \
                                                                                    'Modm count: {}'.format(
            django_model._meta.model.__name__,
            len(django_ids),
            len(django_objects),
            len(page_of_modm_objects),
        )

    for modm_obj in page_of_modm_objects:
        django_obj = django_objects.get(pk=get_pk(modm_obj, django_model, modm_to_django))
        for m2m_field in m2m_relations:
            validate_m2m_field(m2m_field.name, django_obj, modm_obj)
        for fk_field in fk_relations:
            validate_fk_relation(fk_field.name, django_obj, modm_obj)
        for basic_field in basic_fields:
            validate_basic_field(basic_field.name, django_obj, modm_obj)

        count += 1
    logger.info('Through {} {}.{}s...'.format(count, django_model._meta.model.__module__, django_model._meta.model.__name__))


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
                    field.is_relation and not field.auto_created and field.many_to_one]

    basic_fields = [field for field in django_model._meta.get_fields() if not field.is_relation]

    while count < total:
        offset = count
        limit = (count + page_size) if (count + page_size) < total else total
        validate_page_of_model_data.delay(django_model, basic_fields, fk_relations, m2m_relations, offset, limit)
