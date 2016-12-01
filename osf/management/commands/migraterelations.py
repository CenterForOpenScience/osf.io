from __future__ import unicode_literals

import gc
import importlib
import sys

import ipdb
from addons.wiki.models import NodeWikiPage
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.management import BaseCommand
from django.db import transaction
from osf import models
from osf.models import (ApiOAuth2Scope, BlackListGuid, CitationStyle, Guid,
                        Institution, NodeRelation, NotificationSubscription,
                        RecentlyAddedContributor, StoredFileNode, Tag)
from osf.models.base import OptionalGuidMixin
from osf.models.contributor import (AbstractBaseContributor, Contributor,
                                    InstitutionalContributor)
from osf.models.node import AbstractNode, Node
from osf.utils.order_apps import get_ordered_models
from scripts.register_oauth_scopes import set_backend
from website.models import Guid as MODMGuid
from website.models import Institution as MODMInstitution
from website.models import Node as MODMNode
from website.models import NodeLog as MODMNodeLog
from website.models import \
    NotificationSubscription as MODMNotificationSubscription
from website.models import Pointer as MODMPointer
from website.models import User as MODMUser


def build_toku_django_lookup_table_cache(with_guids=False):
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
    models.append(NodeWikiPage)

    lookups = {}

    for model in models:
        if (issubclass(model, AbstractNode) and model is not AbstractNode):
            continue
        lookup_string = model.primary_identifier_name

        lookup_dict = {}

        for mapping in model.objects.all().values(lookup_string, 'pk'):
            if isinstance(mapping[lookup_string], list):
                for guid in mapping[lookup_string]:
                    lookup_dict[unicode(guid)] = mapping['pk']
            else:
                lookup_dict[unicode(mapping[lookup_string])] = mapping['pk']

        if issubclass(model, OptionalGuidMixin):
            for mapping in model.objects.filter(guid_string__isnull=False).values('guid_string', 'guids__pk'):
                if isinstance(mapping['guid_string'], list):
                    for guid in mapping['guid_string']:
                        lookup_dict[unicode(guid)] = mapping['guids__pk']
                else:
                    lookup_dict[unicode(mapping['guid_string'])] = mapping['guids__pk']
        print('Got {} guids for {}'.format(len(lookup_dict), model._meta.model.__name__))
        lookups.update(lookup_dict)

    # add the "special" ones
    lookups.update(
        {u'{}:not_system'.format(x['name']): x['pk'] for x in
         Tag.objects.filter(system=False).values('name', 'pk')})
    lookups.update(
        {u'{}:system'.format(x['name']): x['pk'] for x in
         Tag.objects.filter(system=True).values('name', 'pk')})

    lookups.update({unicode(x['_id']): x['pk']
                    for x in CitationStyle.objects.all().values('_id', 'pk')})
    lookups.update({unicode(x['_id']): x['pk']
                    for x in NotificationSubscription.objects.all().values('_id', 'pk')})
    lookups.update({u'guid:{}'.format(x['_id']): x['pk'] for x in Guid.objects.all().values('_id', 'pk')})
    # institutions used to be nodes but their _id wasn't the 5-str guid it was their assigned institution_id
    # in django their _id is their institution_id which is already added to the list by line 46-68
    institution_guid_mapping = {unicode(x._id): x.node._id for x in MODMInstitution.find(deleted=True)}
    lookups.update(
        {institution_guid_mapping[unicode(x['_id'])]: x['pk']
         for x in Institution.objects.all().values('_id', 'pk')})
    return lookups


def fix_bad_data(django_obj, dirty):
    """
    This fixes a bunch of validation errors that happen during the migration.
    Encapsulating it in one place. Bulk_create doesn't run validation so we
    get to clean it up here.
    :param django_obj:
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

    return (django_obj, dirty)


class Command(BaseCommand):
    help = 'Migrations FK and M2M relationships from tokumx to postgres'
    modm_to_django = None

    def handle(self, *args, **options):
        set_backend()
        models = get_ordered_models()
        with ipdb.launch_ipdb_on_exception():
            self.modm_to_django = build_toku_django_lookup_table_cache(with_guids=True)

        for migration_type in ['fk', 'm2m']:
            with transaction.atomic():
                for django_model in models:
                    if issubclass(django_model, AbstractBaseContributor) \
                            or django_model is ApiOAuth2Scope or \
                            (issubclass(django_model, AbstractNode) and django_model is not AbstractNode) or \
                            not hasattr(django_model, 'modm_model_path'):
                        # if django_model is not NotificationSubscription:
                        continue

                    module_path, model_name = django_model.modm_model_path.rsplit('.', 1)
                    modm_module = importlib.import_module(module_path)
                    modm_model = getattr(modm_module, model_name)
                    if isinstance(django_model.modm_query, dict):
                        modm_queryset = modm_model.find(**django_model.modm_query)
                    else:
                        modm_queryset = modm_model.find(django_model.modm_query)

                    page_size = django_model.migration_page_size

                    with ipdb.launch_ipdb_on_exception():
                        with transaction.atomic():
                            if migration_type == 'fk':
                                self.save_fk_relationships(modm_queryset, django_model, page_size)
                            elif migration_type == 'm2m':
                                self.save_m2m_relationships(modm_queryset, django_model, page_size)
                self.migrate_contributors()


    def save_fk_relationships(self, modm_queryset, django_model, page_size):
        print(
            'Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__name__))

        # TODO: Collections is getting user_id added to the bad fields. It shouldn't be.

        fk_relations = [field for field in django_model._meta.get_fields() if
                        field.is_relation and not field.auto_created and field.many_to_one]

        if len(fk_relations) == 0:
            print('{} doesn\'t have foreign keys.'.format(django_model._meta.model.__name__))
            return
        else:
            print('FKS: {}'.format(fk_relations))
        fk_count = 0
        model_count = 0
        model_total = modm_queryset.count()
        bad_fields = ['external_account_id',]  # external accounts are handled in their own migration

        def format_lookup_string(modm_obj):
            if isinstance(modm_obj, MODMGuid):
                return 'guid:{}'.format(unicode(modm_obj._id).lower())
            if isinstance(modm_obj, basestring):
                try:
                    guid = Guid.objects.get(_id=unicode(modm_obj).lower())
                except Guid.DoesNotExist:
                    # well ... I guess?
                    return unicode(modm_obj).lower()
                else:
                    return u'guid:{}'.format(unicode(modm_obj)).lower()
            return unicode(modm_obj._id).lower()

        while model_count < model_total:
            with transaction.atomic():
                for modm_obj in modm_queryset.sort('-_id')[model_count:model_count + page_size]:
                    if isinstance(modm_obj, MODMNodeLog) and modm_obj.node and modm_obj.node.institution_id:
                        model_count += 1
                        continue
                    django_obj = django_model.objects.get(
                        pk=self.modm_to_django[format_lookup_string(modm_obj)])
                    dirty = False

                    # if an institution has a file, it doesn't
                    # TODO This is doing a mongo query for each Node, could probably be more performant
                    if isinstance(django_obj, StoredFileNode) and modm_obj.node is not None and \
                                    modm_obj.node.institution_id is not None:
                        model_count += 1
                        continue

                    with ipdb.launch_ipdb_on_exception():
                        for field in fk_relations:
                            # notification subscriptions have a AbstractForeignField that's becoming two FKs
                            if isinstance(modm_obj, MODMNotificationSubscription):
                                if isinstance(modm_obj.owner, MODMUser):
                                    # TODO this is also doing a mongo query for each owner
                                    django_obj.user_id = self.modm_to_django[modm_obj.owner._id]
                                    django_obj.node_id = None
                                elif isinstance(modm_obj.owner, MODMNode):
                                    # TODO this is also doing a mongo query for each owner
                                    django_obj.user_id = None
                                    django_obj.node_id = self.modm_to_django[modm_obj.owner._id]
                                elif modm_obj.owner is None:
                                    django_obj.node_id = None
                                    django_obj.user_id = None
                                    print(
                                        'NotificationSubscription {} is abandoned. It\'s owner is {}.'.format(
                                            unicode(modm_obj._id), modm_obj.owner))

                            if isinstance(field, GenericForeignKey):
                                field_name = field.name
                                value = getattr(modm_obj, field_name)
                                if value is None:
                                    continue
                                if value.__class__.__name__ in ['Node', 'Registration', 'Collection',
                                                                'Preprint']:
                                    gfk_model = apps.get_model('osf', 'AbstractNode')
                                else:
                                    gfk_model = apps.get_model('osf', value.__class__.__name__)
                                # TODO in theory, if I saved the content_type_pk in the lookup table this
                                # query
                                # could go away
                                gfk_instance = gfk_model.objects.get(
                                    pk=self.modm_to_django[format_lookup_string(value)])
                                setattr(django_obj, field_name, gfk_instance)
                                dirty = True
                            else:
                                field_name = field.attname
                                if field_name in bad_fields:
                                    continue
                                try:
                                    value = getattr(modm_obj, field_name.replace('_id', ''))
                                except AttributeError:
                                    print('|||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
                                          '||| Couldn\'t find {} adding to bad_fields\n'
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
                                    setattr(django_obj, django_field_name,
                                            self.modm_to_django[format_lookup_string(value)])
                                    dirty = True
                                elif hasattr(value, '_id'):
                                    # let's just assume it's a modm model instance
                                    setattr(django_obj, django_field_name,
                                            self.modm_to_django[format_lookup_string(value)])
                                    dirty = True
                                else:
                                    print('Value is a {}'.format(type(value)))
                                    ipdb.set_trace()

                    django_obj, dirty = fix_bad_data(django_obj, dirty)
                    if dirty:
                        fk_count += 1
                        django_obj.save()
                    model_count += 1
                    if model_count % page_size == 0 or model_count == model_total:
                        print(
                            'Through {} {}s and {} FKs...'.format(model_count,
                                                                  django_model._meta.model.__name__,
                                                                  fk_count))
                        modm_queryset[0]._cache.clear()
                        modm_queryset[0]._object_cache.clear()
                        print('Took out {} trashes'.format(gc.collect()))

                modm_queryset[0]._cache.clear()
                modm_queryset[0]._object_cache.clear()
                print('Took out {} trashes'.format(gc.collect()))

    def save_m2m_relationships(self, modm_queryset, django_model, page_size):
        print(
            'Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__name__))

        m2m_relations = [(field.attname or field.name, field.related_model) for field in
                         django_model._meta.get_fields() if
                         field.is_relation and field.many_to_many and not hasattr(field, 'field')]

        if len(m2m_relations) == 0:
            print(
                '{} doesn\'t have any many to many relationships.'.format(django_model._meta.model.__name__))
            return
        else:
            print('{} M2M relations: {}'.format(django_model._meta.model.__name__, m2m_relations))
        m2m_count = 0
        model_count = 0
        model_total = modm_queryset.count()
        field_aliases = getattr(django_model, 'FIELD_ALIASES', {})
        bad_fields = []

        while model_count < model_total:
            with transaction.atomic():
                for modm_obj in modm_queryset.sort('-_id')[model_count:model_count + page_size]:

                    if django_model is Institution:
                        # If it's an institution look it up by it's institution_id
                        django_obj = django_model.objects.get(
                            pk=self.modm_to_django[unicode(modm_obj.institution_id)]
                        )
                    else:
                        django_obj = django_model.objects.get(pk=self.modm_to_django[unicode(modm_obj._id)])

                    # TODO linked_nodes is getting added to bad fields for AbstractNode

                    for field_name, model in m2m_relations:
                        # figure out a field name based on field_aliases
                        if field_name in ['_contributors', 'external_accounts', 'watched']:
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
                            print('|||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
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
                                    remote_pks.add(self.modm_to_django['{}:system'.format(item)])
                                elif field_name == 'tags' and 'system_tags' in field_aliases.keys():
                                    remote_pks.add(self.modm_to_django['{}:system'.format(item)])
                                elif field_name == 'tags':
                                    remote_pks.add(self.modm_to_django['{}:not_system'.format(item)])
                                else:
                                    remote_pks.add(self.modm_to_django[item])
                            # if it's a class instance
                            elif hasattr(item, '_id'):
                                # grab it's id if it has one.
                                str_value = unicode(item._id)
                                # append the pk to the list of pks
                                if field_name == 'system_tags' and 'system_tags' not in field_aliases.keys():
                                    remote_pks.add(self.modm_to_django['{}:system'.format(str_value)])
                                elif field_name == 'tags' and 'system_tags' in field_aliases.keys():
                                    remote_pks.add(self.modm_to_django['{}:system'.format(str_value)])
                                elif field_name == 'tags':
                                    remote_pks.add(self.modm_to_django['{}:not_system'.format(str_value)])
                                else:
                                    remote_pks.add(self.modm_to_django[str_value])
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
                                rel_dict = {}
                                rel_dict['{}_id'.format(source_field_name)] = django_obj.pk
                                rel_dict['{}_id'.format(target_field_name)] = remote_pk
                                django_objects.append(field_model_instance(**rel_dict))
                            field_model_instance.objects.bulk_create(django_objects)
                            m2m_count += len(django_objects)
                    model_count += 1
                    if model_count % page_size == 0 or model_count == model_total:
                        modm_queryset[0]._cache.clear()
                        modm_queryset[0]._object_cache.clear()
                        print('Took out {} trashes'.format(gc.collect()))
                        print(
                            'Through {} {}s and {} m2m'.format(model_count, django_model._meta.model.__name__,
                                                               m2m_count))

    def migrate_node_through_models(self):
        print('Starting {}...'.format(sys._getframe().f_code.co_name))
        if not self.modm_to_django.keys():
            self.modm_to_django = build_toku_django_lookup_table_cache()
        total = MODMNode.find().count()
        count = 0
        contributor_count = 0
        node_relation_count = 0
        page_size = Node.migration_page_size
        contributors = []

        with transaction.atomic():
            while count < total:
                with transaction.atomic():
                    for modm_obj in MODMNode.find().sort('-_id')[count:page_size + count]:
                        order = 0
                        hashes = set()
                        for modm_contributor in modm_obj.contributors:
                            read = 'read' in modm_obj.permissions[unicode(modm_contributor._id)]
                            write = 'write' in modm_obj.permissions[unicode(modm_contributor._id)]
                            admin = 'admin' in modm_obj.permissions[unicode(modm_contributor._id)]
                            visible = unicode(modm_contributor._id) in modm_obj.visible_contributor_ids
                            if (self.modm_to_django[unicode(modm_contributor._id)],
                                self.modm_to_django[unicode(modm_obj._id)]) not in hashes:
                                contributors.append(
                                    Contributor(
                                        read=read,
                                        write=write,
                                        admin=admin,
                                        user_id=self.modm_to_django[unicode(modm_contributor._id)],
                                        node_id=self.modm_to_django[unicode(modm_obj._id)],
                                        _order=order,
                                        visible=visible
                                    )
                                )
                                hashes.add((self.modm_to_django[unicode(modm_contributor._id)],
                                            self.modm_to_django[unicode(modm_obj._id)]))
                                order += 1
                                contributor_count += 1
                            else:
                                print('({},{}) already in hashes.'.format(
                                    self.modm_to_django[unicode(modm_contributor._id)],
                                    self.modm_to_django[unicode(modm_obj._id)]))
                        count += 1

                        if count % page_size == 0 or count == total:
                            Contributor.objects.bulk_create(contributors)
                            print('Through {} nodes and {} contributors, '
                                  'saved {} contributors'.format(count, contributor_count, len(contributors)))
                            contributors = []
                            modm_obj._cache.clear()
                            modm_obj._object_cache.clear()
                            print('Took out {} trashes'.format(gc.collect()))

                        node_relations = []
                        for modm_node in modm_obj.nodes:
                            parent_id = self.modm_to_django[unicode(modm_obj._id)]
                            child_id = self.modm_to_django[unicode(modm_obj._id)]
                            if isinstance(modm_node, MODMPointer):
                                node_relations.append(
                                    NodeRelation(
                                        _id=modm_node._id,  # preserve GUID on pointers
                                        is_node_link=True,
                                        parent_id=parent_id,
                                        child_id=child_id
                                    )
                                )
                            else:
                                node_relations.append(
                                    NodeRelation(
                                        is_node_link=False,
                                        parent_id=parent_id,
                                        child_id=child_id
                                    )
                                )
                            node_relation_count += 1

                        if count % page_size == 0 or count == total:
                            NodeRelation.objects.bulk_create(node_relations)
                            print('Through {} nodes and {} node relations, '
                                  'saved {} NodeRelations'
                                  .format(count, node_relation_count, len(node_relations)))
                            contributors = []
                            modm_obj._cache.clear()
                            modm_obj._object_cache.clear()
                            print('Took out {} trashes'.format(gc.collect()))
