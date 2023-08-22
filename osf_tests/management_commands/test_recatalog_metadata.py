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


@pytest.mark.django_db
class TestRecatalogMetadata:

    @pytest.fixture
    def mock_update_share_task(self):
        with mock.patch('osf.management.commands.recatalog_metadata.task__update_share') as _shmock:
            yield _shmock

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

    @pytest.fixture
    def files(self, preprints):
        _files = sorted_by_id([
            preprint.primary_file
            for preprint in preprints
        ])
        for _file in _files:
            _file.get_guid(create=True)
        return _files

    @pytest.fixture
    def users(self, preprints, registrations, projects):
        return sorted_by_id(list(set([
            project.creator
            for project in projects
        ] + [
            registration.creator
            for registration in registrations
        ] + [
            preprint.creator
            for preprint in preprints
        ])))

    def test_recatalog_metadata(self, mock_update_share_task, preprint_provider, preprints, registration_provider, registrations, projects, files, users):
        # test preprints
        call_command(
            'recatalog_metadata',
            '--preprints',
            '--providers',
            preprint_provider._id,
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(preprints)

        mock_update_share_task.reset_mock()

        # test registrations
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--providers',
            registration_provider._id,
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(registrations)

        mock_update_share_task.reset_mock()

        # test projects
        call_command(
            'recatalog_metadata',
            '--projects',
            '--all-providers',
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(projects)

        mock_update_share_task.reset_mock()

        # test files
        call_command(
            'recatalog_metadata',
            '--files',
            '--all-providers',
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(files)

        mock_update_share_task.reset_mock()

        # test users
        call_command(
            'recatalog_metadata',
            '--users',
            '--all-providers',
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(users)

        mock_update_share_task.reset_mock()

        # test chunking
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--all-providers',
            f'--start-id={registrations[1].id}',
            '--chunk-size=3',
            '--chunk-count=1',
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(registrations[1:4])

        mock_update_share_task.reset_mock()

        # slightly different chunking
        call_command(
            'recatalog_metadata',
            '--registrations',
            '--all-providers',
            f'--start-id={registrations[2].id}',
            '--chunk-size=2',
            '--chunk-count=2',
        )
        assert mock_update_share_task.apply_async.mock_calls == expected_apply_async_calls(registrations[2:6])


###
# local utils

def expected_apply_async_calls(items):
    return [
        mock.call(kwargs={
            'guid': _item.guids.values_list('_id', flat=True).first(),
            'is_backfill': True,
        })
        for _item in items
    ]


def sorted_by_id(things_with_ids):
    return sorted(
        things_with_ids,
        key=attrgetter('id')
    )
