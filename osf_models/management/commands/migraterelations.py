import gc
import importlib
import sys

import ipdb
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from osf_models import models
from osf_models.models import ApiOAuth2Scope
from osf_models.models import BlackListGuid
from osf_models.models import CitationStyle
from osf_models.models import Guid
from osf_models.models import Institution
from osf_models.models import NodeLog
from osf_models.models import NotificationSubscription
from osf_models.models import RecentlyAddedContributor
from osf_models.models import StoredFileNode
from osf_models.models import Tag
from osf_models.models.base import OptionalGuidMixin
from osf_models.models.contributor import InstitutionalContributor, Contributor, AbstractBaseContributor
from osf_models.models.node import AbstractNode, Node
from osf_models.utils.order_apps import get_ordered_models
from website.models import Guid as MODMGuid
from website.models import Institution as MODMInstitution
from website.models import NotificationSubscription as MODMNotificationSubscription
from website.models import Node as MODMNode
from website.models import User as MODMUser
from website.models import NodeLog as MODMNodeLog


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

    lookups = {}

    for model in models:
        if (issubclass(model, AbstractNode) and model is not AbstractNode):
            continue
        lookup_string = model.primary_identifier_name

        lookup_dict = {}

        for mapping in model.objects.all().values(lookup_string, 'pk'):
            if isinstance(mapping[lookup_string], list):
                for guid in mapping[lookup_string]:
                    lookup_dict[guid] = mapping['pk']
            else:
                lookup_dict[mapping[lookup_string]] = mapping['pk']

        if issubclass(model, OptionalGuidMixin):
            for mapping in model.objects.filter(guid_string__isnull=False).values('guid_string', 'guids__pk'):
                if isinstance(mapping['guid_string'], list):
                    for guid in mapping['guid_string']:
                        lookup_dict[guid] = mapping['guids__pk']
                else:
                    lookup_dict[mapping['guid_string']] = mapping['guids__pk']
        print('Got {} guids for {}'.format(len(lookup_dict), model._meta.model.__name__))
        lookups.update(lookup_dict)

    # add the "special" ones
    lookups.update(
        {u'{}:not_system'.format(x['name']): x['pk'] for x in
         Tag.objects.filter(system=False).values('name', 'pk')})
    lookups.update(
        {u'{}:system'.format(x['name']): x['pk'] for x in
         Tag.objects.filter(system=True).values('name', 'pk')})
    lookups.update({x['_id']: x['pk'] for x in CitationStyle.objects.all().values('_id', 'pk')})
    lookups.update({x['_id']: x['pk'] for x in NotificationSubscription.objects.all().values('_id', 'pk')})
    lookups.update({u'guid:{}'.format(x['_id']): x['pk'] for x in Guid.objects.all().values('_id', 'pk')})
    # institutions used to be nodes but their _id wasn't the 5-str guid it was their assigned institution_id
    # in django their _id is their institution_id which is already added to the list by line 46-68
    institution_guid_mapping = {x._id: x.node._id for x in MODMInstitution.find(deleted=True)}
    lookups.update({institution_guid_mapping[x['_id']]: x['pk'] for x in Institution.objects.all().values('_id', 'pk')})
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
        models = get_ordered_models()
        with ipdb.launch_ipdb_on_exception():
            self.modm_to_django = build_toku_django_lookup_table_cache(with_guids=True)

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
                self.save_fk_relationships(modm_queryset, django_model, page_size)
                # self.save_m2m_relationships(modm_queryset, django_model, page_size)

    def save_fk_relationships(self, modm_queryset, django_model, page_size):
        print(
            'Starting {} on {}...'.format(sys._getframe().f_code.co_name, django_model._meta.model.__name__))

        # TODO: Collections is getting user_id added to the bad fields. It shouldn't be.
        # TODO: Comment.root is getting a recursive loop
        # TODO children of AbstractNode are failing in fk migrations.
        # TODO something is wrong with comments

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
        bad_fields = []

        def format_lookup_string(modm_obj):
            if isinstance(modm_obj, MODMGuid):
                return 'guid:{}'.format(modm_obj._id)
            if isinstance(modm_obj, basestring):
                try:
                    guid = Guid.objects.get(_id=modm_obj)
                except Guid.DoesNotExist:
                    # well ... I guess?
                    return modm_obj
                else:
                    return 'guid:{}'.format(modm_obj)
            return modm_obj._id


        while model_count < model_total:
            with transaction.atomic():
                for modm_obj in modm_queryset.sort('-_id')[model_count:model_count + page_size]:
                    if isinstance(modm_obj, MODMNodeLog) and modm_obj.node and modm_obj.node.institution_id:
                        model_count+=1
                        continue
                    django_obj = django_model.objects.get(pk=self.modm_to_django[format_lookup_string(modm_obj)])
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
                                    django_obj.node_id = self.modm_to_django[modm_obj.owner._id]
                                    django_obj.user_id = None
                                elif modm_obj.owner is None:
                                    django_obj.node_id = None
                                    django_obj.user_id = None
                                    print('NotificationSubscription {} is abandoned. It\'s owner is {}.'.format(modm_obj._id, modm_obj.owner))

                            if isinstance(field, GenericForeignKey):
                                field_name = field.name
                                value = getattr(modm_obj, field_name)
                                if value is None:
                                    continue
                                if value.__class__.__name__ in ['Node', 'Registration', 'Collection', 'Preprint']:
                                    gfk_model = apps.get_model('osf_models', 'AbstractNode')
                                else:
                                    gfk_model = apps.get_model('osf_models', value.__class__.__name__)
                                # TODO in theory, if I saved the content_type_pk in the lookup table this query
                                # could go away
                                gfk_instance = gfk_model.objects.get(pk=self.modm_to_django[format_lookup_string(value)])
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
                                          '|||||||||||||||||||||||||||||||||||||||||||||||||||||||'.format(
                                        field_name.replace('_id', '')))
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
                                    setattr(django_obj, django_field_name, self.modm_to_django[format_lookup_string(value)])
                                    dirty = True
                                elif hasattr(value, '_id'):
                                    # let's just assume it's a modm model instance
                                    setattr(django_obj, django_field_name, self.modm_to_django[format_lookup_string(value)])
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
        m2m_relations = [(field.attname or field.name, field.related_model) for field in django_model._meta.get_fields() if field.is_relation and not field.auto_created and field.many_to_many]

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
                        django_obj = django_model.objects.get(pk=self.modm_to_django[modm_obj.institution_id])
                    else:
                        django_obj = django_model.objects.get(pk=self.modm_to_django[modm_obj._id])
                    for field_name, model in m2m_relations:
                        if field_name in bad_fields:
                            continue
                        django_field_name = None
                        if field_name in field_aliases.values():
                            django_field_name = {v:k for k, v in field_aliases.iteritems()}[field_name]
                        django_pks = []
                        try:
                            if field_name in bad_fields:
                                continue
                            try:
                                value = getattr(modm_obj, field_name)
                            except AttributeError:
                                print('|||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
                                      '||| Couldn\'t find {} adding to bad_fields\n'
                                      '|||||||||||||||||||||||||||||||||||||||||||||||||||||||'.format(
                                    field_name))
                                bad_fields.append(field_name)
                                value = []
                            if len(value) < 1:
                                continue
                        except AttributeError:
                            print(
                                'MODM: {} doesn\'t have a {} attribute.'.format(
                                    django_model._meta.model.__name__,
                                    field_name))
                            ipdb.set_trace()
                        else:
                            for item in value:
                                if isinstance(item, basestring):
                                    if field_name == 'system_tags':
                                        django_pks.append(self.modm_to_django['{}:system'.format(item)])
                                    elif field_name == 'tags':
                                        django_pks.append(self.modm_to_django['{}:not_system'.format(item)])
                                    else:
                                        django_pks.append(self.modm_to_django[item])
                                elif type(item) == type:
                                    if hasattr(item, '_id'):
                                        str_value = item._id
                                    else:
                                        # wth is it
                                        ipdb.set_trace()
                                    if field_name == 'system_tags':
                                        django_pks.append(self.modm_to_django['{}:system'.format(str_value)])
                                    elif field_name == 'tags':
                                        django_pks.append(self.modm_to_django['{}:not_system'.format(str_value)])
                                    else:
                                        django_pks.append(self.modm_to_django[str_value])
                        try:
                            if django_field_name:
                                attr = getattr(django_obj, django_field_name)
                            else:
                                attr = getattr(django_obj, field_name)
                        except AttributeError:
                            print('DJANGO: {} doesn\'t have a {} attribute.'.format(
                                django_model._meta.model.__name__, field_name))
                            ipdb.set_trace()

                        if len(django_pks) > 0:
                            ipdb.set_trace()
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                    model_count += 1
                    if model_count % page_size == 0 or model_count == model_total:
                        print(
                            'Through {} {}s and {} m2m'.format(model_count, django_model._meta.model.__name__,
                                                               m2m_count))
        print('Done with {} in {} seconds...'.format(sys._getframe().f_code.co_name, (timezone.now())))
