import pytest
from unittest import mock
from operator import attrgetter

from django.core.management import call_command

from osf_tests.factories import (
    PreprintProviderFactory,
    PreprintFactory,
    ProjectFactory,
    RegistrationProviderFactory,
    RegistrationFactory,
)


def sorted_by_id(things_with_ids):
    return sorted(
        things_with_ids,
        key=attrgetter('id')
    )


@pytest.mark.django_db
class TestRecatalogMetadata:

    @pytest.fixture
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture
    def preprints(self, preprint_provider):
        return sorted_by_id([
            PreprintFactory(provider=preprint_provider)
            for _ in range(7)
        ])

    @pytest.fixture
    def registration_provider(self):
        return RegistrationProviderFactory()

    @pytest.fixture
    def registrations(self, registration_provider):
        return sorted_by_id([
            RegistrationFactory(provider=registration_provider)
            for _ in range(7)
        ])

    @pytest.fixture
    def projects(self, registrations):
        return sorted_by_id([
            ProjectFactory()
            for _ in range(7)
        ] + [
            registration.registered_from
            for registration in registrations
        ])

    @mock.patch('api.share.utils.update_share')
    def test_recatalog_metadata(self, mock_update_share, preprint_provider, preprints, registration_provider, registrations, projects):

        # test preprints
        call_command(
            'recatalog_metadata',
            '--preprints',
            '--providers',
            preprint_provider._id,
        )
        expected_update_share_calls = [
            mock.call(preprint)
            for preprint in preprints
        ]
        assert mock_update_share.mock_calls == expected_update_share_calls

        mock_update_share.reset_mock()

        # test registrations
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--providers',
            registration_provider._id,
        )
        expected_update_share_calls = [
            mock.call(registration)
            for registration in registrations
        ]
        assert mock_update_share.mock_calls == expected_update_share_calls

        mock_update_share.reset_mock()

        # test projects
        call_command(
            'recatalog_metadata',
            '--projects',
            '--all-providers',
        )
        expected_update_share_calls = [
            mock.call(project)
            for project in projects  # already ordered by id
        ]
        assert mock_update_share.mock_calls == expected_update_share_calls

        mock_update_share.reset_mock()

        # test chunking
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--all-providers',
            f'--start-id={registrations[1].id}',
            '--chunk-size=3',
            '--chunk-count=1',
        )
        expected_update_share_calls = [
            mock.call(registration)
            for registration in registrations[1:4]
        ]
        assert mock_update_share.mock_calls == expected_update_share_calls

        mock_update_share.reset_mock()

        # slightly different chunking
        expected_update_share_calls = [
            mock.call(registration)
            for registration in registrations[2:6]  # already ordered by id
        ]
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--all-providers',
            f'--start-id={registrations[2].id}',
            '--chunk-size=2',
            '--chunk-count=2',
        )
        assert mock_update_share.mock_calls == expected_update_share_calls
