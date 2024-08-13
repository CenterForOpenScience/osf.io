import pytest
from unittest import mock
from operator import attrgetter
import random

from django.core.management import call_command

from osf.models.metadata import GuidMetadataRecord
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

    @pytest.fixture
    def items_with_custom_datacite_type(self, preprints, registrations, projects, files):
        _nonpreprint_sample = [
            random.choice(_items)
            for _items in (registrations, projects, files)
        ]
        for _item in _nonpreprint_sample:
            _guid_record = GuidMetadataRecord.objects.for_guid(_item)
            _guid_record.resource_type_general = 'BookChapter'  # datacite resourceTypeGeneral value
            _guid_record.save()
        return {
            *preprints,  # every preprint has datacite type "Preprint"
            *_nonpreprint_sample,
        }

    def test_recatalog_metadata(
        self,
        mock_update_share_task,
        preprint_provider,
        preprints,
        registration_provider,
        registrations,
        projects,
        files,
        users,
        items_with_custom_datacite_type,
    ):
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

        mock_update_share_task.reset_mock()

        # datacite custom types
        call_command(
            'recatalog_metadata',
            '--datacite-custom-types',
        )
        _expected_osfids = set(_iter_osfids(items_with_custom_datacite_type))
        _actual_osfids = {
            _call[-1]['kwargs']['guid']
            for _call in mock_update_share_task.apply_async.mock_calls
        }
        assert _expected_osfids == _actual_osfids


###
# local utils

def expected_apply_async_calls(items):
    return [
        mock.call(
            kwargs={
                'guid': _osfid,
                'is_backfill': True,
            },
            queue='low',
        )
        for _osfid in _iter_osfids(items)
    ]


def _iter_osfids(items):
    for _item in items:
        yield _item.guids.values_list('_id', flat=True).first()


def sorted_by_id(things_with_ids):
    return sorted(
        things_with_ids,
        key=attrgetter('id')
    )
