import pytest
from bulk_update.helper import bulk_update
from django.db.models import CharField, Max

from osf_tests.factories import RegistrationFactory, NodeFactory, UserFactory


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
    def test_update_objects(self, Factory):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())
        new_ids = [o.id for o in objects]
        charfield = [x.name for x in objects[0]._meta.get_fields() if isinstance(x, CharField)][0]
        qs = objects[0]._meta.model.objects.filter(id__in=new_ids)
        assert len(qs) > 0, 'No results returned'
        try:
            count = qs.update(**{charfield: 'things'})
        except Exception as ex:
            pytest.fail('Queryset update failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))


    @pytest.mark.parametrize('Factory', guid_factories)
    def test_related_manager(self, Factory):
        thing_with_logs = Factory()
        assert hasattr(thing_with_logs, 'logs'), 'Thing must have logs.'

        try:
            thing_with_logs.logs.all()
        except Exception as ex:
            pytest.fail('Related manager failed for {} with exception {}'.format(Factory._meta.model.__name__, ex))

    @pytest.mark.parametrize('Factory', guid_factories)
    def test_count_objects(self, Factory):
        objects = []
        things = range(0, 5)
        for thing in things:
            objects.append(Factory())
        new_ids = [o.id for o in objects]
        qs = objects[0]._meta.model.objects.filter(id__in=new_ids)
        count = qs.count()
        assert count == len(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    def test_bulk_create_objects(self, Factory):
        if Factory is RegistrationFactory:
            raise pytest.skip('Registrations cannot be created without saving')
        objects = []
        ids = range(0, 5)
        Model = Factory._meta.model
        for id in ids:
            objects.append(Factory.build(id=id))
        things = Model.objects.bulk_create(objects)
        assert len(things) == len(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    def test_bulk_update_objects(self, Factory):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())
        charfield = [x.name for x in objects[0]._meta.get_fields() if isinstance(x, CharField)][0]
        for obj in objects:
            setattr(obj, charfield, 'things')
        bulk_update(objects)

    @pytest.mark.parametrize('Factory', guid_factories)
    def test_annotate(self, Factory):
        objects = []
        ids = range(0, 5)
        for id in ids:
            objects.append(Factory())

        things = Factory._meta.model.objects.all().annotate(highest_id=Max('id'))
        for thing in things:
            assert hasattr(thing, 'highest_id'), 'Annotation failed'
