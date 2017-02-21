import pytest
from bulk_update.helper import bulk_update
from django.db.models import CharField, Max

from osf_tests.factories import RegistrationFactory, NodeFactory, UserFactory, PreprintFactory


@pytest.mark.django_db
class TestGuidAnnotations:
    guid_factories = [
        UserFactory,
        NodeFactory,
        RegistrationFactory,
    ]

    @pytest.mark.parametrize('Factory', guid_factories)
    def test_filter_object(self, Factory):
        obj = Factory()
        assert 'guids__' in str(obj._meta.model.objects.filter(id=obj.id).query), 'Guid annotations did not exist in filter query for {}'.format(obj._meta.model.__name__)

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_update_objects(self, Factory, django_assert_num_queries):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())
        new_ids = [o.id for o in objects]
        try:
            charfield = [x.name for x in objects[0]._meta.get_fields() if isinstance(x, CharField)][0]
        except IndexError:
            pytest.skip('Thing doesn\'t have a CharField')
        qs = objects[0]._meta.model.objects.filter(id__in=new_ids)
        assert len(qs) > 0, 'No results returned'
        try:
            with django_assert_num_queries(1):
                count = qs.update(**{charfield: 'things'})
        except Exception as ex:
            pytest.fail('Queryset update failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_related_manager(self, Factory, django_assert_num_queries):
        thing_with_logs = Factory()
        if not hasattr(thing_with_logs, 'logs'):
            pytest.skip('Thing must have logs')

        try:
            with django_assert_num_queries(1):
                wow = list(thing_with_logs.logs.all())
        except Exception as ex:
            pytest.fail('Related manager failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_related_manager_values_list(self, Factory, django_assert_num_queries):
        thing_with_logs = Factory()
        if not hasattr(thing_with_logs, 'contributors'):
            pytest.skip('Thing must have contributors')

        try:
            with django_assert_num_queries(1):
                stuff = list(thing_with_logs.contributors.values_list('guids___id'))
        except Exception as ex:
            pytest.fail('Values list failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_related_manager_values_list_flat(self, Factory, django_assert_num_queries):
        thing_with_logs = Factory()
        if not hasattr(thing_with_logs, 'contributors'):
            pytest.skip('Thing must have contributors')

        try:
            with django_assert_num_queries(1):
                alot = list(thing_with_logs.contributors.values_list('guids___id', flat=True))
        except Exception as ex:
            pytest.fail('Values list failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_related_manager_values(self, Factory, django_assert_num_queries):
        thing_with_logs = Factory()
        if not hasattr(thing_with_logs, 'contributors'):
            pytest.skip('Thing must have contributors')

        try:
            with django_assert_num_queries(1):
                ohmai = list(thing_with_logs.contributors.values('guids___id'))
        except Exception as ex:
            pytest.fail('Values list failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_count_objects(self, Factory, django_assert_num_queries):
        objects = []
        things = range(0, 5)
        for thing in things:
            objects.append(Factory())
        new_ids = [o.id for o in objects]
        with django_assert_num_queries(1):
            qs = objects[0]._meta.model.objects.filter(id__in=new_ids)
            count = qs.count()
        assert count == len(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_bulk_create_objects(self, Factory, django_assert_num_queries):
        if Factory is RegistrationFactory:
            raise pytest.skip('Registrations cannot be created without saving')
        objects = []
        ids = range(0, 5)
        Model = Factory._meta.model
        for id in ids:
            objects.append(Factory.build(id=id))
        with django_assert_num_queries(1):
            things = Model.objects.bulk_create(objects)
        assert len(things) == len(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_bulk_update_objects(self, Factory, django_assert_num_queries):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())
        charfield = [x.name for x in objects[0]._meta.get_fields() if isinstance(x, CharField)][0]
        for obj in objects:
            setattr(obj, charfield, 'things')
        with django_assert_num_queries(1):
            bulk_update(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    @pytest.mark.django_assert_num_queries
    def test_annotate(self, Factory, django_assert_num_queries):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())
        with django_assert_num_queries(1):
            things = Factory._meta.model.objects.all().annotate(highest_id=Max('id'))
        for thing in things:
            assert hasattr(thing, 'highest_id'), 'Annotation failed'
