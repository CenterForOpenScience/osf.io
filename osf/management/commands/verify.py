from __future__ import unicode_literals
from __future__ import print_function

import importlib

import gc
import ipdb
import sys

from datetime import datetime

import pytz
from django.core.management import BaseCommand
from osf.management.commands.migratedata import register_nonexistent_models_with_modm
from osf.management.commands.migraterelations import build_toku_django_lookup_table_cache
from osf.models import BlackListGuid
from osf.models import Institution
from osf.models import Tag
from osf.utils.order_apps import get_ordered_models
from scripts.register_oauth_scopes import set_backend


class NotGonnaDoItException(BaseException):
    pass


class Command(BaseCommand):
    help = 'Validates migrations from tokumx to postgres'

    def handle(self, *args, **options):
        set_backend()

        register_nonexistent_models_with_modm()

        self.modm_to_django = build_toku_django_lookup_table_cache()

        django_models = get_ordered_models()

        for django_model in django_models:

            if not hasattr(django_model, 'modm_model_path'):
                print('################################################\n'
                      '{} doesn\'t have a modm_model_path\n'
                      '################################################'.format(
                    django_model._meta.model.__name__))
                continue
            elif django_model is Tag or django_model is BlackListGuid:
                # we'll do this by hand because tags are special
                # we'll do blacklistguids by hand because they've got a bunch of new ones that don't exist in modm
                # specifically, from register_none_existent_models
                continue

            module_path, model_name = django_model.modm_model_path.rsplit('.', 1)
            modm_module = importlib.import_module(module_path)
            modm_model = getattr(modm_module, model_name)
            if isinstance(django_model.modm_query, dict):
                modm_queryset = modm_model.find(**django_model.modm_query)
            else:
                modm_queryset = modm_model.find(django_model.modm_query)

            with ipdb.launch_ipdb_on_exception():
                self.validate_model_data(modm_queryset, django_model, page_size=django_model.migration_page_size)

            modm_model._cache.clear()
            modm_model._object_cache.clear()
            print('Took out {} trashes'.format(gc.collect()))

    def validate_m2m_field(self, field_name, django_obj, modm_obj):
        # TODO need to make this smarter
        # it should introspect the related object, use it's primary_identifier_name and use
        # that to compare itself and the modm thingies

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

    def validate_fk_relation(self, field_name, django_obj, modm_obj):
        if field_name in ['content_type', 'content_type_id']:
            # modm doesn't have gfk
            return
        assert getattr(django_obj, field_name)._id == getattr(modm_obj, field_name)._id

    def validate_basic_field(self, field_name, django_obj, modm_obj):
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

    def get_pk(self, modm_object):
        from website.models import Tag as MODMTag
        from website.models import Guid as MODMGuid

        key = unicode(modm_object._id).lower()

        if key in self.modm_to_django:
            return self.modm_to_django[key]
        elif isinstance(modm_object, MODMTag):
            raise NotGonnaDoItException('Can\'t get pk for tag.')
        elif isinstance(modm_object, MODMGuid):
            return self.modm_to_django['guid:{}'.format(modm_object._id)]

    def validate_model_data(self, modm_queryset, django_model, page_size=20000):
        print('Starting {} on {}...'.format(
            sys._getframe().f_code.co_name, django_model._meta.model.__name__))
        count = 0
        field_count = 0
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

            page_of_modm_objects = modm_queryset.sort('-_id')[offset:limit]
            django_ids = [self.get_pk(modm_obj) for modm_obj in page_of_modm_objects]
            django_objects = django_model.objects.filter(id__in=django_ids)

            assert len(django_ids) == len(django_objects) == len(page_of_modm_objects), 'Lost some keys along the way for {}'.format(django_model._meta.model.__name__)

            for modm_obj in page_of_modm_objects:
                django_obj = django_objects.get(pk=self.get_pk(modm_obj))
                for m2m_field in m2m_relations:
                    self.validate_m2m_field(m2m_field.name, django_obj, modm_obj)
                    field_count += 1
                for fk_field in fk_relations:
                    self.validate_fk_relation(fk_field.name, django_obj, modm_obj)
                    field_count += 1
                for basic_field in basic_fields:
                    self.validate_basic_field(basic_field.name, django_obj, modm_obj)
                    field_count += 1

                count += 1

                if count % page_size == 0 or count == total:
                    print('Through {} {}s and {} fields...'.format(count, django_model._meta.model.__name__, field_count))

                    modm_queryset[0]._cache.clear()
                    modm_queryset[0]._object_cache.clear()
                    print('Took out {} trashes...'.format(gc.collect()))
