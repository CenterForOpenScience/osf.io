import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory
)
from django.shortcuts import reverse



@pytest.mark.django_db
class TestInstitutionRegistrationList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'title',
            'type',
            'date_modified',
            'date_created',
            'storage_location',
            'storage_usage',
            'is_public',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200

