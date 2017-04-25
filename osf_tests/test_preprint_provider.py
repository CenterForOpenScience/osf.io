import pytest

from django.core.exceptions import ValidationError

from factories import PreprintProviderFactory
from website.project.model import ensure_schemas

pytestmark = pytest.mark.django_db

@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory()

class TestPreprintProviderValidation:

    @pytest.fixture(autouse=True)
    def _ensure_schemas(self):
        return ensure_schemas()

    def test_blank_extra_valid(self, preprint_provider):
        extra = {}
        setattr(preprint_provider, 'extra', extra)
        preprint_provider.save()
        assert preprint_provider.extra == {}

    def test_invalid_extra_description(self, preprint_provider):
        extra = {
            'description': []
        }
        setattr(preprint_provider, 'extra', extra)
        with pytest.raises(ValidationError) as excinfo:
            preprint_provider.save()
        assert excinfo.value.message_dict == {'extra': ["[] is not of type u'string'"]}

    def test_valid_extra_description(self, preprint_provider):
        extra = {
            'description': 'A scholarly commons to connect the entire research cycle'
        }
        setattr(preprint_provider, 'extra', extra)
        preprint_provider.save()
        assert preprint_provider.extra == extra

    def test_invalid_extra_advisory_board(self, preprint_provider):
        extra = {
            'advisory_board': {
                'groups': [{
                    'group_name': 'Steering Committee',
                    'members': 'Nevets Longoria, Ostriches'
                }]
            }
        }
        setattr(preprint_provider, 'extra', extra)
        with pytest.raises(ValidationError) as excinfo:
            preprint_provider.save()
        assert excinfo.value.message_dict == {'extra': ["'Nevets Longoria, Ostriches' is not of type u'array'"]}

    def test_valid_extra_advisory_board(self, preprint_provider):
        extra = {
            'advisory_board': {
                'groups': [{
                    'group_name': 'Steering Committee',
                    'members': [
                        {
                            'name': 'Nevets Longoria',
                            'role': 'Nugget Aficionado',
                        },
                        {
                            'name': 'Ostriches',
                            'role': 'Alternative Wisecarver'
                        }
                    ]
                }]
            }
        }
        setattr(preprint_provider, 'extra', extra)
        preprint_provider.save()
        assert preprint_provider.extra == extra

    def test_invalid_extra_social(self, preprint_provider):
        extra = {
            'social_facebook': 'CenterForOpenScience',
            'social_twitter': 'osframework'
        }
        setattr(preprint_provider, 'extra', extra)
        with pytest.raises(ValidationError) as excinfo:
            preprint_provider.save()
        assert excinfo.value.message_dict == {'extra': ["Additional properties are not allowed ('social_facebook', 'social_twitter' were unexpected)"]}

    def test_valid_extra_social(self, preprint_provider):
        extra = {
            'social': {
                'facebook': 'CenterForOpenScience',
                'twitter': 'osframework'
            }
        }
        setattr(preprint_provider, 'extra', extra)
        preprint_provider.save()
        assert preprint_provider.extra == extra

