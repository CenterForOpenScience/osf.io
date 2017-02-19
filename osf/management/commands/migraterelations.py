from __future__ import unicode_literals

import logging
import pstats
import sys
import traceback
from cProfile import Profile

import ipdb
from bulk_update.helper import bulk_update
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import transaction

from addons.osfstorage.models import NodeSettings as OSFStorageNodeSettings
from addons.wiki.models import NodeSettings as WikiNodeSettings
from api.base.celery import app
from osf import models
from osf.models import (ApiOAuth2Scope, BlackListGuid, CitationStyle, Guid,
                        Institution, NodeRelation, NotificationSubscription,
                        RecentlyAddedContributor, StoredFileNode, Tag)
from osf.models import OSFUser
from osf.models.contributor import (AbstractBaseContributor, Contributor,
                                    InstitutionalContributor)
from osf.models.node import AbstractNode, Node
from osf.utils.order_apps import get_ordered_models
from website.app import init_app
from website.models import Institution as MODMInstitution
from website.models import Node as MODMNode
from website.models import \
    NotificationSubscription as MODMNotificationSubscription
from website.models import Pointer as MODMPointer
from website.models import User as MODMUser
from .migratedata import set_backend, get_modm_model, register_nonexistent_models_with_modm

logger = logging.getLogger('migrations')


class HashableDict(dict):
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


def build_toku_django_lookup_table_cache():
    models = get_ordered_models()

    # ignored models
    models.pop(models.index(BlackListGuid))
    models.pop(models.index(RecentlyAddedContributor))
    models.pop(models.index(Contributor))
    models.pop(models.index(InstitutionalContributor))

    # "special" models
    models.pop(models.index(Tag))
    models.pop(models.index(CitationStyle))
    models.pop(models.index(NotificationSubscription))

    models.pop(models.index(Guid))

    lookups = {}
    for model in models:
        res = do_model_lookup(model)
        if not res:
            continue
        lookups.update(res)

    # add the "special" ones
    lookups.update(
        {format_lookup_key(x['name'], ContentType.objects.get_for_model(Tag).pk, template='{}:not_system'): x['pk'] for x in
         Tag.objects.filter(system=False).values('name', 'pk')})
    lookups.update(
        {format_lookup_key(x['name'], ContentType.objects.get_for_model(Tag).pk, template='{}:system'): x['pk'] for x in
         Tag.objects.filter(system=True).values('name', 'pk')})

    lookups.update({format_lookup_key(x['_id'], ContentType.objects.get_for_model(CitationStyle).pk): x['pk']
                    for x in CitationStyle.objects.all().values('_id', 'pk')})
    lookups.update({format_lookup_key(x['_id'], ContentType.objects.get_for_model(NotificationSubscription).pk): x['pk']
                    for x in NotificationSubscription.objects.all().values('_id', 'pk')})
    lookups.update({format_lookup_key(x['_id'], ContentType.objects.get_for_model(Guid).pk): x['pk'] for x in Guid.objects.all().values('_id', 'pk')})

    # institutions used to be nodes but their _id wasn't the 5-str guid it was their assigned institution_id
    # in django their _id is their institution_id which is already added to the list by line 60-71

    # make a list of MODMInstitution._id to MODMInstitution.node._id
    institution_guid_mapping = {x._id: x.node._id for x in MODMInstitution.find(deleted=True)}
    # update lookups with institution ct, x.node._id -> pk
    lookups.update({format_lookup_key(institution_guid_mapping[x['_id']], ContentType.objects.get_for_model(Institution).pk): x['pk'] for x in Institution.objects.all().values('_id', 'pk')})

    # make a list of MODMInstitution._id to MODMInstitution.node._id
    institution_guid_mapping = {x._id: x.node._id for x in MODMInstitution.find(deleted=True)}
    # update lookups with node_ct, x.node._id -> pk
    lookups.update({format_lookup_key(institution_guid_mapping[x['_id']], ContentType.objects.get_for_model(Node).pk): x['pk'] for x in Institution.objects.all().values('_id', 'pk')})
    return lookups


def do_model_lookup(model):
    if issubclass(model, AbstractNode) and model is not AbstractNode:
        return
    lookup_string = model.primary_identifier_name
    lookup_dict = {}

    content_type_pk = ContentType.objects.get_for_model(model).pk
    for guid_string, pk in model.objects.all().values_list(lookup_string, 'pk'):
        if isinstance(guid_string, list):
            for guid in guid_string:
                lookup_key = format_lookup_key(guid, content_type_pk)
                # if lookup_key in lookup_dict:
                    # logger.info('Key {} exists with value {} but {} tried to replace it.'.format(lookup_key, lookup_dict[lookup_key], pk))
                lookup_dict[lookup_key] = pk
        else:
            lookup_key = format_lookup_key(guid_string, content_type_pk)
            # if lookup_key in lookup_dict:
                # logger.info('Key {} exists with value {} but {} tried to replace it.'.format(lookup_key, lookup_dict[lookup_key], pk))
            lookup_dict[lookup_key] = pk
    # logger.info('Got {} guids for {}.{}'.format(len(lookup_dict), model._meta.model.__module__, model._meta.model.__module__))
    return lookup_dict


def fix_bad_data(django_obj, dirty):
    """
    This fixes a bunch of validation errors that happen during the migration.
    Encapsulating it in one place. Bulk_create doesn't run validation so we
    get to clean it up here.
    :param django_obj: The django object in question
    :param dirty: Whether or not the model instance was dirty on entry
    :return:
    """
    if isinstance(django_obj, models.Node):
        if django_obj.title.strip() == '':
            django_obj.title = 'Blank Title'
            dirty = True

    if isinstance(django_obj, models.Embargo):
        if django_obj.state == 'active':
            django_obj.state = 'completed'
            dirty = True
        elif django_obj.state == 'cancelled':
            django_obj.state = 'rejected'
            dirty = True

    if isinstance(django_obj, models.Retraction):
        if django_obj.state == 'cancelled':
            django_obj.state = 'rejected'
            dirty = True
        if django_obj.state == 'retracted':
            django_obj.state = 'completed'
            dirty = True
        if django_obj.state == 'pending':
            django_obj.state = 'unapproved'
            dirty = True

    return django_obj, dirty


def format_lookup_key(guid, content_type_id=None, model=None, template=None):
    if not content_type_id and model:
        content_type_id = ContentType.objects.get_for_model(model).pk
    elif not content_type_id and not model:
        raise Exception('Please specify either a content_type_id or a model')
    if template:
        return content_type_id, template.format(unicode(guid).lower())
    return content_type_id, unicode(guid).lower()


def get_pk_for_unknown_node_model(modm_to_django, guid):
    abstract_node_subclasses = AbstractNode.__subclasses__()
    abstract_node_subclasses.append(Institution)

    for model in abstract_node_subclasses:
        key = format_lookup_key(guid, model=model)
        try:
            pk = modm_to_django[key]
        except KeyError:
            logger.error('modm key {} not found in lookup table'.format(
                format_lookup_key(guid, ContentType.objects.get_for_model(model).pk)))
        else:
            return pk

    logger.error('Could not find key for {} guid'.format(guid))


@app.task()
def do_model(django_model, *args, **options):
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()

    if issubclass(django_model, AbstractBaseContributor) \
            or django_model is ApiOAuth2Scope or \
            (issubclass(django_model, AbstractNode) and django_model is not AbstractNode) or \
            not hasattr(django_model, 'modm_model_path'):
        return

    page_size = django_model.migration_page_size

# with ipdb.launch_ipdb_on_exception():
    try:
        if options['fk']:
            logger.info('Starting fk migrations...')
            save_fk_relationships.delay(django_model, page_size)
        elif options['m2m']:
            logger.info('Starting m2m migrations...')
            save_m2m_relationships.delay(django_model, page_size)

    except Exception as ex:
        logger.info('##################################################{} just died on {}.#############################################################'.format(django_model, ex))
        raise ex


@app.task(bind=True, max_retries=None)  # retry forever because of deadlocks
def save_page_of_fk_relationships(self, django_model, fk_relations, offset, limit):
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()
    # Disable typedmodel auto-recasting to prevent migration from missing fields h/t @chrisseto
    AbstractNode._auto_recast = False
    try:
        with transaction.atomic():  # one transaction per page
            bad_fields = []

            modm_model = get_modm_model(django_model)
            if isinstance(django_model.modm_query, dict):
                modm_queryset = modm_model.find(**django_model.modm_query)
            else:
                modm_queryset = modm_model.find(django_model.modm_query)

            modm_page = modm_queryset.sort('_id')[offset:limit]
            model_count = 0
            fk_count = 0
            modm_keys = modm_page.get_keys()
            modm_to_django = build_toku_django_lookup_table_cache()

            django_keys = []
            for modm_key in modm_keys:
                try:
                    django_keys.append(modm_to_django[
                                           format_lookup_key(modm_key, ContentType.objects.get_for_model(django_model).pk)])
                except KeyError as ex:
                    if format_lookup_key(modm_key, model=django_model)[1].startswith(
                            'none_') and django_model is NotificationSubscription:
                        logger.info('{!r} NotificationSubscription is bad data, skipping'.format(modm_key))
                        model_count += 1
                        continue
                    else:
                        logger.error('modm key {} not found in lookup table'.format(format_lookup_key(modm_key, ContentType.objects.get_for_model(django_model).pk)))
                        continue
            django_objects = django_model.objects.filter(pk__in=django_keys)
            django_objects_to_update = []
            django_objects_dict = {obj.pk: obj for obj in django_objects}
            for modm_obj in modm_page:
                try:
                    django_obj = django_objects_dict[modm_to_django[format_lookup_key(modm_obj._id, model=django_model)]]
                except KeyError as ex:
                    logger.error('modm key {} not found in lookup table'.format(format_lookup_key(modm_obj._id, ContentType.objects.get_for_model(django_model).pk)))
                    continue
                if django_model is OSFUser:
                    dirty = True
                else:
                    dirty = False

                # TODO This is doing a mongo query for each Node, could probably be more performant
                # if an institution has a file, it doesn't
                if isinstance(django_obj, StoredFileNode) and modm_obj.node is not None and \
                                modm_obj.node.institution_id is not None:
                    model_count += 1
                    continue
                # If we're migrating a NodeSetting pointing at an institution then commit seppuku
                if isinstance(django_obj, (WikiNodeSettings, OSFStorageNodeSettings)) and modm_obj.owner is not None and modm_obj.owner.institution_id is not None:
                    model_count += 1
                    continue
                # notification subscriptions have a AbstractForeignField that's becoming two FKs
                if isinstance(modm_obj, MODMNotificationSubscription):
                    if isinstance(modm_obj.owner, MODMUser):
                        # TODO this is also doing a mongo query for each owner
                        django_obj.user_id = modm_to_django[format_lookup_key(modm_obj.owner._id, model=OSFUser)]
                        django_obj.node_id = None
                        dirty = True
                        fk_count += 1
                    elif isinstance(modm_obj.owner, MODMNode):
                        # TODO this is also doing a mongo query for each owner
                        django_obj.user_id = None
                        django_obj.node_id = modm_to_django[format_lookup_key(modm_obj.owner._id, model=AbstractNode)]
                        dirty = True
                        fk_count += 1
                    elif modm_obj.owner is None:
                        django_obj.node_id = None
                        django_obj.user_id = None
                        dirty = True
                        logger.info(
                            'NotificationSubscription {!r} is abandoned. It\'s owner is {!r}.'.format(
                                unicode(modm_obj._id), modm_obj.owner))
                    else:
                        logger.error('NotificationSubscription {} owner was {}'.format(modm_obj._id, modm_obj.owner.__repr__()))


                    # with ipdb.launch_ipdb_on_exception():
                for field in fk_relations:
                    value = None
                    if isinstance(field, GenericForeignKey):
                        field_name = field.name
                        ct_field_name = field.ct_field
                        fk_field_name = field.fk_field
                        value = getattr(modm_obj, field_name)
                        if value is None:
                            continue
                        if value.__class__.__name__ in ['Node', 'Registration', 'Collection', 'Preprint']:
                            gfk_model = apps.get_model('osf', 'AbstractNode')
                        else:
                            gfk_model = apps.get_model('osf', value.__class__.__name__)

                        content_type_primary_key, formatted_guid = format_lookup_key(value._id, model=gfk_model)
                        try:
                            fk_field_value = modm_to_django[(content_type_primary_key, formatted_guid)]
                        except KeyError as ex:
                            logger.error('modm key {} not found in lookup table'.format(
                                format_lookup_key(modm_obj._id, model=django_model)))
                            continue

                        # this next line could be better if we just got all the content_types
                        setattr(django_obj, ct_field_name, ContentType.objects.get_for_model(gfk_model))
                        setattr(django_obj, fk_field_name, fk_field_value)
                        dirty = True
                        fk_count += 1

                    else:
                        field_name = field.attname
                        if field_name in bad_fields:
                            continue
                        try:
                            value = getattr(modm_obj, field_name.replace('_id', ''))
                        except AttributeError:
                            logger.info('|||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
                                        '||| Couldn\'t find {!r} adding to bad_fields\n'
                                        '|||||||||||||||||||||||||||||||||||||||||||||||||||||||'
                                        .format(field_name.replace('_id', '')))
                            bad_fields.append(field_name)
                            value = None
                        if value is None:
                            continue

                        if field_name.endswith('_id'):
                            django_field_name = field_name
                        else:
                            django_field_name = '{}_id'.format(field_name)

                        if isinstance(value, basestring):
                            # it's guid as a string
                            try:
                                setattr(django_obj, django_field_name,
                                        modm_to_django[format_lookup_key(value, model=field.related_model)])
                            except KeyError as ex:
                                logger.error('modm key {} not found in lookup table'.format(
                                    format_lookup_key(modm_obj._id, model=django_model)))
                                continue
                            else:
                                dirty = True
                                fk_count += 1

                        elif hasattr(value, '_id'):
                            # let's just assume it's a modm model instance
                            try:
                                setattr(django_obj, django_field_name,
                                        modm_to_django[format_lookup_key(value._id, model=field.related_model)])
                            except KeyError as ex:
                                logger.error('modm key {} not found in lookup table'.format(
                                    format_lookup_key(modm_obj._id, model=django_model)))
                                continue
                            dirty = True
                            fk_count += 1

                        else:
                            logger.info('Value is a {!r}'.format(type(value)))
                            ipdb.set_trace()

                django_obj, dirty = fix_bad_data(django_obj, dirty)
                if dirty:
                    django_objects_to_update.append(django_obj)
                model_count += 1
            logger.info(
                'Through {} {}.{}s and {} FKs...'.format(model_count,
                                                      django_model._meta.model.__module__,
                                                      django_model._meta.model.__name__,
                                                      fk_count))
            if django_objects_to_update:
                if django_model is OSFUser:
                    winning = [u.save() for u in django_objects_to_update]
                else:
                    n_objects_to_update = len(django_objects_to_update)
                    if n_objects_to_update > 1000:
                        batch_size = n_objects_to_update // 5
                    else:
                        batch_size = None
                    bulk_update(django_objects_to_update, batch_size=batch_size)

            modm_obj._cache.clear()
            modm_obj._object_cache.clear()

    except Exception as ex:
        logger.error('Retrying: Failed to save page model: {} offset:{} limit:{} of foreign keys with exception {}'.format(django_model, offset, limit, ex.message))
        self.retry(countdown=60)  # retry in 1m
    finally:
        # Disable typedmodel auto-recasting to prevent migration from missing fields h/t @chrisseto
        AbstractNode._auto_recast = True


@app.task()
def save_fk_relationships(django_model, page_size):
    logger.info(
        'Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__module__))
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()
    fk_relations = [field for field in django_model._meta.get_fields() if
                    field.is_relation and not field.auto_created and (field.many_to_one or field.one_to_one)]

    if len(fk_relations) == 0:
        logger.info('{} doesn\'t have foreign keys.'.format(django_model._meta.model.__module__))
        return
    else:
        logger.info('{} FK relations:'.format(django_model._meta.model.__module__))
        for rel in fk_relations:
            logger.info('{!r}'.format(rel))
    model_count = 0
    modm_model = get_modm_model(django_model)
    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)
    model_total = modm_queryset.count()

    while model_count < model_total:
        logger.info('{}.{} starting'.format(django_model._meta.model.__module__, django_model._meta.model.__name__))
        save_page_of_fk_relationships.delay(django_model, fk_relations, model_count, model_count+page_size)
        model_count += page_size


@app.task(bind=True)
def save_page_of_m2m_relationships(self, django_model, m2m_relations, offset, limit):
    try:
        with transaction.atomic():  # one transaction per page
            modm_model = get_modm_model(django_model)
            modm_to_django = build_toku_django_lookup_table_cache()
            if isinstance(django_model.modm_query, dict):
                modm_queryset = modm_model.find(**django_model.modm_query)
            else:
                modm_queryset = modm_model.find(django_model.modm_query)

            modm_page = modm_queryset.sort('-_id')[offset:limit]
            model_count = 0
            m2m_count = 0
            field_aliases = getattr(django_model, 'FIELD_ALIASES', {})
            bad_fields = ['_nodes', 'contributors']  # we'll handle noderelations and contributors by hand
            added_relationships = dict()
            # {
            #   'field_name' : set(rel_dict, rel_dict, rel_dict),
            #   'field_name' : set(rel_dict, rel_dict, rel_dict),
            #   'field_name' : set(rel_dict, rel_dict, rel_dict),
            # }

            for modm_obj in modm_page:
                try:
                    if django_model is Institution:
                        # If it's an institution look it up by it's institution_id
                        django_obj = django_model.objects.get(
                            pk=modm_to_django[format_lookup_key(modm_obj.institution_id, model=django_model)]
                        )
                    else:
                        try:
                            django_obj = django_model.objects.get(pk=modm_to_django[format_lookup_key(modm_obj._id, model=django_model)])
                        except Exception as ex:
                            query = str(django_model.objects.filter(pk=modm_to_django[format_lookup_key(modm_obj._id, model=django_model)]).query)
                            pks = modm_to_django[format_lookup_key(modm_obj._id, model=django_model)]
                            logger.error('{} for {} at {} with pk of {}\n'
                                         'query: {}'.format(ex, django_model, format_lookup_key(modm_obj._id, model=django_model), pks, query))
                            raise ex
                except KeyError as ex:
                    logger.error('modm key {} not found in lookup table'.format(format_lookup_key(modm_obj._id, model=django_model)))
                    continue

                # TODO linked_nodes is getting added to bad fields for AbstractNode
                for field_name, model in m2m_relations:
                    # figure out a field name based on field_aliases
                    if field_name in ['_contributors', 'watched']:
                        # these are handled elsewhere
                        continue
                    django_field_name = None
                    if field_name in field_aliases.values():
                        django_field_name = {v: k for k, v in field_aliases.iteritems()}[field_name]

                    remote_pks = set()
                    # skip fields that have been marked as bad
                    if field_name in bad_fields:
                        continue

                    try:
                        if not django_field_name:
                            value = getattr(modm_obj, field_name)
                        else:
                            value = getattr(modm_obj, django_field_name)
                    except AttributeError:
                        logger.info('|||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
                                    '||| Couldn\'t find {} adding to bad_fields\n'
                                    '|||||||||||||||||||||||||||||||||||||||||||||||||||||||'
                                    .format(field_name))
                        # if we get an attribute error print debugging and mark the field to skip
                        bad_fields.append(field_name)
                        value = []

                    # there's a m2m, list of stuff, if the list is empty, skip
                    if len(value) < 1:
                        continue

                    # for each rel in the m2m
                    for item in value:
                        # if it's a string, probably guid
                        if isinstance(item, basestring):
                            # append the pk to the list of pks
                            if field_name == 'system_tags' and 'system_tags' not in field_aliases.keys():
                                try:
                                    remote_pks.add(modm_to_django[format_lookup_key(item, model=model, template='{}:system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            elif field_name == 'tags' and 'system_tags' in field_aliases.keys():
                                try:
                                    remote_pks.add(modm_to_django[format_lookup_key(item, model=model, template='{}:system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            elif field_name == 'tags':
                                try:
                                    remote_pks.add(
                                        modm_to_django[format_lookup_key(item, model=model, template='{}:not_system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            else:
                                try:
                                    remote_pks.add(modm_to_django[format_lookup_key(item, model=model)])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                        # if it's a class instance
                        elif hasattr(item, '_id'):
                            # grab it's id if it has one.
                            str_value = item._id
                            # append the pk to the list of pks
                            if field_name == 'system_tags' and 'system_tags' not in field_aliases.keys():
                                try:
                                    remote_pks.add(
                                        modm_to_django[format_lookup_key(str_value, model=model, template='{}:system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            elif field_name == 'tags' and 'system_tags' in field_aliases.keys():
                                try:
                                    remote_pks.add(
                                        modm_to_django[format_lookup_key(str_value, model=model, template='{}:system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            elif field_name == 'tags':
                                try:
                                    remote_pks.add(
                                        modm_to_django[format_lookup_key(str_value, model=model, template='{}:not_system')])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                            else:
                                try:
                                    remote_pks.add(modm_to_django[format_lookup_key(str_value, model=model)])
                                except KeyError as ex:
                                    logger.error('{} for {} at {}'.format(ex, django_model,
                                                                    format_lookup_key(modm_obj._id, model=django_model)))
                                    continue
                        elif item is None:
                            continue
                        else:
                            # wth is it
                            ipdb.set_trace()

                    # if the list of pks isn't empty
                    if len(remote_pks) > 0:
                        django_objects = []
                        field = getattr(django_obj, field_name)
                        source_field_name = field.source_field.name
                        target_field_name = field.target_field.name
                        field_model_instance = field.through
                        for remote_pk in remote_pks:
                            # rel_dict is a dict of the properties of the through model
                            rel_dict = HashableDict()
                            rel_dict['{}_id'.format(source_field_name)] = django_obj.pk
                            rel_dict['{}_id'.format(target_field_name)] = remote_pk
                            if field_name not in added_relationships:
                                added_relationships[field_name] = set()
                            if rel_dict not in added_relationships[field_name]:
                                added_relationships[field_name].add(rel_dict)
                                django_objects.append(field_model_instance(**rel_dict))
                            else:
                                logger.info('Relation {} already exists for {}'.format(rel_dict, field_name))
                        if len(django_objects) > 1000:
                            batch_size = len(django_objects) // 5
                        else:
                            batch_size = len(django_objects)
                            field_model_instance.objects.bulk_create(django_objects, batch_size=batch_size)
                        m2m_count += len(django_objects)
                model_count += 1
            logger.info(
                'Through {} {}s and {} m2m'.format(model_count, django_model._meta.model.__module__,
                                                   m2m_count))
    except Exception as ex:
        tb = traceback.format_exc()
        logger.error(
            'Retrying: Failed to save page {} offset:{} limit:{} of m2m with exception {}\n{}'.format(django_model, offset, limit, ex, tb))
        self.retry(countdown=60)  # retry in 1m

@app.task()
def save_m2m_relationships(django_model, page_size):
    logger.info(
        'Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__module__))

    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()

    m2m_relations = [(field.attname or field.name, field.related_model) for field in
                     django_model._meta.get_fields() if
                     field.is_relation and field.many_to_many and not hasattr(field, 'field')]

    if len(m2m_relations) == 0:
        logger.info(
            '{} doesn\'t have any many to many relationships.'.format(django_model._meta.model.__module__))
        return
    else:
        logger.info('{} M2M relations:'.format(django_model._meta.model.__module__))
        for rel in m2m_relations:
            logger.info('{}'.format(rel))

    model_count = 0
    modm_model = get_modm_model(django_model)
    if isinstance(django_model.modm_query, dict):
        modm_queryset = modm_model.find(**django_model.modm_query)
    else:
        modm_queryset = modm_model.find(django_model.modm_query)
    model_total = modm_queryset.count()

    while model_count < model_total:
        save_page_of_m2m_relationships.delay(django_model, m2m_relations, model_count, model_count+page_size)
        model_count += page_size


class Command(BaseCommand):
    help = 'Migrations FK and M2M relationships from tokumx to postgres'
    modm_to_django = None

    def add_arguments(self, parser):
        parser.add_argument('--profile', action='store', help='Filename to dump profiling information')
        parser.add_argument('--fk', action='store_true', help='Run fk migrations')
        parser.add_argument('--m2m', action='store_true', help='Run m2m migrations')

    def handle(self, *args, **options):
        init_app(routes=False, attach_request_handlers=False, fixtures=False)
        set_backend()
        register_nonexistent_models_with_modm()
        if options['profile']:
            profiler = Profile()
            profiler.runcall(self._handle, *args, **options)
            stats = pstats.Stats(profiler).sort_stats('cumulative')
            stats.print_stats()
            stats.dump_stats(options['profile'])
        else:
            self._handle(*args, **options)

    def _handle(self, *args, **options):
        init_app(routes=False, attach_request_handlers=False, fixtures=False)
        set_backend()
        register_nonexistent_models_with_modm()
        models = get_ordered_models()
    # with ipdb.launch_ipdb_on_exception():
        if not options['m2m'] and not options['fk']:
            return

        for model in models:
            do_model.delay(model, **options)
        if options['m2m']:
            migrate_node_through_models.delay()
            migration_institutional_contributors.delay()


@app.task()
def migration_institutional_contributors():
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()

    modm_to_django = build_toku_django_lookup_table_cache()
    total = MODMInstitution.find(deleted=True).count()
    count = 0
    contributor_count = 0
    page_size = Institution.migration_page_size
    contributors = []
    contributor_hashes = set()
# with ipdb.launch_ipdb_on_exception():
    institutions = MODMInstitution.find(deleted=True).sort('-_id')
    while count < total:
        with transaction.atomic():  # one transaction per page.
            for modm_obj in institutions[count:page_size + count]:
                clean_institution_guid = unicode(modm_obj.node._id).lower()
                for modm_contributor in modm_obj.contributors:
                    clean_user_guid = unicode(modm_contributor._id).lower()
                    read = 'read' in modm_obj.permissions[clean_user_guid]
                    write = 'write' in modm_obj.permissions[clean_user_guid]
                    admin = 'admin' in modm_obj.permissions[clean_user_guid]
                    visible = clean_user_guid in modm_obj.visible_contributor_ids

                    if (
                            modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                            get_pk_for_unknown_node_model(modm_to_django, clean_institution_guid)
                    ) not in contributor_hashes:
                        contributors.append(
                            InstitutionalContributor(
                                read=read,
                                write=write,
                                admin=admin,
                                user_id=modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                                institution_id=get_pk_for_unknown_node_model(modm_to_django, clean_institution_guid),
                                visible=visible
                            )
                        )
                        contributor_hashes.add((modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                                                get_pk_for_unknown_node_model(modm_to_django, clean_institution_guid)))
                        contributor_count += 1
                    else:
                        logger.info('({},{}) already in institutional contributor_hashes.'.format(
                            modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                            get_pk_for_unknown_node_model(modm_to_django, clean_institution_guid)))
                count += 1

                if count % page_size == 0 or count == total:
                    InstitutionalContributor.objects.bulk_create(contributors)
                    logger.info('Through {} nodes and {} institutional contributors, '
                                'saved {} institutional contributors'.format(count, contributor_count, len(contributors)))
                    contributors = []
                    modm_obj._cache.clear()
                    modm_obj._object_cache.clear()

@app.task()
def migrate_node_through_models():
    logger.info('Starting {}...'.format(sys._getframe().f_code.co_name))
    init_app(routes=False, attach_request_handlers=False, fixtures=False)
    set_backend()
    register_nonexistent_models_with_modm()

    modm_to_django = build_toku_django_lookup_table_cache()
    total = MODMNode.find().count()
    count = 0
    contributor_count = 0
    node_relation_count = 0
    page_size = Node.migration_page_size
    contributors = []
    node_relations = []
    node_rel_hashes = set()
    contributor_hashes = set()
# with ipdb.launch_ipdb_on_exception():
    nodes = MODMNode.find().sort('-_id')
    while count < total:
        with transaction.atomic():  # one transaction per page.
            # is this query okay? isn't it going to catch things we don't want?
            for modm_obj in nodes[count:page_size + count]:
                order = 0
                clean_node_guid = unicode(modm_obj._id).lower()
                perms = modm_obj.permissions
                lower_case_perms = {unicode(k).lower(): v for k, v in perms.iteritems()}
                lower_visible_contributor_ids = [unicode(i).lower() for i in modm_obj.visible_contributor_ids]
                for modm_contributor in modm_obj.contributors:
                    clean_user_guid = unicode(modm_contributor._id).lower()
                    read = 'read' in lower_case_perms[clean_user_guid]
                    write = 'write' in lower_case_perms[clean_user_guid]
                    admin = 'admin' in lower_case_perms[clean_user_guid]
                    visible = clean_user_guid in lower_visible_contributor_ids

                    if (
                            modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                            get_pk_for_unknown_node_model(modm_to_django, clean_node_guid)
                    ) not in contributor_hashes:
                        contributors.append(
                            Contributor(
                                read=read,
                                write=write,
                                admin=admin,
                                user_id=modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                                node_id=get_pk_for_unknown_node_model(modm_to_django, clean_node_guid),
                                _order=order,
                                visible=visible
                            )
                        )
                        contributor_hashes.add((modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                                                get_pk_for_unknown_node_model(modm_to_django, clean_node_guid)))
                        order += 1
                        contributor_count += 1
                    else:
                        logger.info('({},{}) already in contributor_hashes.'.format(
                            modm_to_django[format_lookup_key(clean_user_guid, model=OSFUser)],
                            get_pk_for_unknown_node_model(modm_to_django, clean_node_guid)))
                count += 1

                if count % page_size == 0 or count == total:
                    Contributor.objects.bulk_create(contributors)
                    logger.info('Through {} nodes and {} contributors, '
                                'saved {} contributors'.format(count, contributor_count, len(contributors)))
                    contributors = []
                    modm_obj._cache.clear()
                    modm_obj._object_cache.clear()

                noderel_order = 0
                for modm_node in modm_obj.nodes:
                    parent_id = modm_to_django[format_lookup_key(clean_node_guid, model=Node)]
                    if isinstance(modm_node, MODMPointer):
                        child_id = get_pk_for_unknown_node_model(modm_to_django, modm_node.node._id)
                    else:
                        child_id = get_pk_for_unknown_node_model(modm_to_django, modm_node._id)
                    if not (parent_id, child_id) in node_rel_hashes:
                        if isinstance(modm_node, MODMPointer):
                            node_relations.append(
                                NodeRelation(
                                    _id=modm_node._id,  # preserve GUID on pointers
                                    is_node_link=True,
                                    parent_id=parent_id,
                                    child_id=child_id,
                                    _order=noderel_order
                                )
                            )
                        else:
                            node_relations.append(
                                NodeRelation(
                                    is_node_link=False,
                                    parent_id=parent_id,
                                    child_id=child_id,
                                    _order=noderel_order
                                )
                            )
                        node_rel_hashes.add((parent_id, child_id))
                        node_relation_count += 1
                        noderel_order += 1

                if count % page_size == 0 or count == total:
                    NodeRelation.objects.bulk_create(node_relations)
                    logger.info('Through {} nodes and {} node relations, '
                                'saved {} NodeRelations'
                                .format(count, node_relation_count, len(node_relations)))
                    node_relations = []
                    modm_obj._cache.clear()
                    modm_obj._object_cache.clear()
