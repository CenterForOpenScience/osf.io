import pytest

from .factories import ExternalAccountFactory

@pytest.mark.django_db
class TestEncryptedStringField:
    def test_values_match(self):
        ao2af = ExternalAccountFactory()
        encrypted_field_names = [f.name for f in ExternalAccountFactory._meta.model.get_fields() if ]
