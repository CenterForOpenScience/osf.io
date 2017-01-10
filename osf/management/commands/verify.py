from __future__ import unicode_literals
from __future__ import print_function

import importlib

import gc
import ipdb
import sys
from django.core.management import BaseCommand
from osf.management.commands.migratedata import register_nonexistent_models_with_modm
from osf.management.commands.migraterelations import build_toku_django_lookup_table_cache
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
            elif django_model is Tag:
                # we'll do this by hand because tags are special
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
        django_guids = getattr(django_obj, field_name).all().values('guids___id')
        assert getattr(django_obj, field_name)._id == getattr(modm_obj, field_name)._id

    def validate_fk_relation(self, field_name, django_obj, modm_obj):
        assert getattr(django_obj, field_name)._id == getattr(modm_obj, field_name)._id

    def validate_basic_field(self, field_name, django_obj, modm_obj):
        assert getattr(django_obj, field_name) == getattr(modm_obj, field_name)

    def get_pk(self, modm_object):
        from website.models import Tag as MODMTag
        from website.models import Guid as MODMGuid
        key = unicode(modm_object._id)
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
            django_ids = [self.modm_to_django[self.get_pk(modm_obj)] for modm_obj in page_of_modm_objects]
            django_objects = django_model.objects.filter(id__in=django_ids)
            django_objects_by_modm_id = {obj._id: obj for obj in django_objects}

            assert len(django_ids) == len(django_objects) == len(page_of_modm_objects), 'Lost some keys along the way for {}'.format(django_model._meta.model.__name__)

            for modm_obj in page_of_modm_objects:
                try:
                    django_obj = django_objects_by_modm_id[modm_obj._id]
                except KeyError:
                    ipdb.set_trace()
                else:
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
