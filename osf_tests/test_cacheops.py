import pytest
from nose.tools import assert_equal

from osf.models import AbstractNode
from osf.models import Registration
from osf_tests.factories import RegistrationFactory


@pytest.fixture()
def title():
    return 'whoa, that\'s a thing'


@pytest.fixture()
def registration(title):
    return RegistrationFactory(title=title)


@pytest.fixture()
def registration1(title):
    return RegistrationFactory(title=title)


@pytest.mark.django_db
class TestCacheOps(object):
    @pytest.mark.settings
    def test_typedmodels_works_with_cacheops(self, registration, settings):
        settings.CACHEOPS_ENABLED = True
        reg = Registration.objects.get(id=registration.id)

        ab = AbstractNode.objects.get(id=reg.id)

        original_title = reg.title
        original_reg_id = reg.id
        assert reg.title == ab.title

        new_title = 'But cacheops'
        reg.title = new_title
        reg.save()

        updated_reg = Registration.objects.get(id=original_reg_id)
        assert_equal(updated_reg.title, new_title)

        updated_abstractnode = AbstractNode.objects.get(id=original_reg_id)

        assert updated_abstractnode.title == new_title

    @pytest.mark.settings
    @pytest.mark.django_assert_num_queries
    def test_typedmodels_queryset_works_with_cacheops(self, django_assert_num_queries, title, registration, registration1, settings):
        settings.CACHEOPS_ENABLED = True
        reg_qs = Registration.objects.filter(title=title)
        ab_qs = AbstractNode.objects.filter(id__in=[registration.id, registration1.id])
        with django_assert_num_queries(2):
            assert reg_qs.count() == ab_qs.count()

        with django_assert_num_queries(2):
            ab_obj = ab_qs.first()
            reg_obj = reg_qs.first()

        assert ab_obj.id == reg_obj.id
        assert ab_obj.title == reg_obj.title

        reg_obj.title = 'oh, no no'
        reg_obj.save()

        with django_assert_num_queries(1):
            ab_qs1 = AbstractNode.objects.filter(id__in=[registration.id, registration1.id])
            ab_obj1 = ab_qs1.first()

        assert reg_obj.title == ab_obj1.title








