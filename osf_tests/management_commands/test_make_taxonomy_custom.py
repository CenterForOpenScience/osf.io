import pytest

from django.core.management import call_command

from osf_tests.factories import PreprintProviderFactory

@pytest.mark.django_db
class TestMakeTaxonomyCustom:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    def test_make_custom_taxonomy(self, provider):
        assert provider.subjects.count() == 0

        call_command('make_taxonomy_custom', f'-id={provider._id}')
        assert provider.subjects.count() == 1217

        with pytest.raises(AssertionError) as e:
            call_command('make_taxonomy_custom', f'-id={provider._id}')

        assert str(e.value) == 'This provider already has a custom taxonomy'
