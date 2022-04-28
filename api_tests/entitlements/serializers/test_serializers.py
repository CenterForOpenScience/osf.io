import pytest
from api.entitlements.serializers import LoginAvailabilitySerializer


@pytest.mark.django_db
class TestLoginAvailabilitySerializer:

    def test_serializer(self):
        id_test = '1'
        payload = {
            'institution_id': id_test,
            'entitlements': ['gkn1-ent1', 'gkn1-ent2', 'gkn1-ent1']
        }
        data = LoginAvailabilitySerializer(data=payload)
        assert data.is_valid() is True

        data = data.validated_data
        institution_id = data.get('institution_id')

        assert institution_id == id_test
