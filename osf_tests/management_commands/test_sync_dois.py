import pytest
import datetime
from django.utils import timezone

from django.core.management import call_command

from osf_tests.factories import (
    PreprintFactory,
    RegistrationFactory,
)

from website import settings


@pytest.mark.django_db
class TestSyncDOIs:

    @pytest.fixture()
    def preprint(self):
        preprint = PreprintFactory()
        doi = preprint.get_doi_client().build_doi(preprint)
        preprint.set_identifier_value('doi', doi)
        return preprint

    @pytest.fixture()
    def registration(self):
        registration = RegistrationFactory()
        doi = registration.request_identifier_update('doi')
        registration.set_identifier_value('doi', doi)
        registration.is_public = True
        registration.save()
        return registration

    @pytest.fixture()
    def registration_identifier(self, registration):
        identifier = registration.identifiers.first()
        identifier.modified = timezone.now() - datetime.timedelta(days=1)
        identifier.save(update_modified=False)
        return identifier

    @pytest.fixture()
    def preprint_identifier(self, preprint):
        identifier = preprint.identifiers.first()
        identifier.modified = timezone.now() - datetime.timedelta(days=1)
        identifier.save(update_modified=False)
        return identifier

    @pytest.mark.enable_enqueue_task
    def test_doi_synced_datacite(self, app, registration, registration_identifier, mock_datacite):
        assert registration_identifier.modified.date() < datetime.datetime.now().date()

        call_command('sync_doi_metadata', f'-m={datetime.datetime.now()}')
        assert len(mock_datacite.calls) == 2
        update_metadata, update_doi = mock_datacite.calls
        assert update_metadata.request.url == f'{settings.DATACITE_URL}/metadata'
        assert update_doi.request.url == f'{settings.DATACITE_URL}/doi'

        registration_identifier.reload()
        assert registration_identifier.modified.date() == datetime.datetime.now().date()

    @pytest.mark.enable_enqueue_task
    def test_doi_synced_crossref(self, app, preprint_identifier, mock_crossref):
        assert preprint_identifier.modified.date() < datetime.datetime.now().date()

        call_command('sync_doi_metadata', f'-m={datetime.datetime.now()}')

        assert len(mock_crossref.calls) == 1

        preprint_identifier.reload()
        assert preprint_identifier.modified.date() == datetime.datetime.now().date()
