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
class TestInstitutionFilesList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'file_name',
            'file_path',
            'date_modified',
            'date_created',
            'mime_type',
            'size',
            'resource_type',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200
