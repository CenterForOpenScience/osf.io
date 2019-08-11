# -*- coding: utf-8 -*-
import pytest

from osf.models import RegistrationSchema


@pytest.mark.django_db
class TestRegistrationSchema:

    @pytest.fixture()
    def schema_name(self):
        return 'Preregistration Template from AsPredicted.org'

    @pytest.fixture()
    def schema_v2(self, schema_name):
        v2 = RegistrationSchema.objects.create(name=schema_name, schema_version=2)
        return v2

    @pytest.fixture()
    def schema_v3(self, schema_name):
        return RegistrationSchema.objects.get(name=schema_name, schema_version=3)

    def test_get_latest_versions(self, schema_v2, schema_v3):
        latest_versions = RegistrationSchema.objects.get_latest_versions()
        assert schema_v3 in latest_versions
        assert schema_v2 not in latest_versions

    def test_get_latest_version(self, schema_name):
        assert RegistrationSchema.objects.get_latest_version(name=schema_name).schema_version == 3
