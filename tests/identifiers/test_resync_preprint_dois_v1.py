import pytest
from datetime import timedelta
from unittest import mock
from django.core.management import call_command
from django.utils import timezone

from osf.models import Preprint
from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.management.commands.resync_preprint_dois_v1 import (
    get_preprints_needing_v1_doi,
    resync_preprint_dois_v1,
    resync_preprint_dois_v1_task,
)
from website import settings

pytestmark = pytest.mark.django_db


@pytest.fixture()
def provider():
    p = PreprintProviderFactory()
    p.doi_prefix = '10.31219'
    p.save()
    return p


@pytest.fixture()
def preprint(provider):
    pp = PreprintFactory(provider=provider, is_published=True)
    old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
    pp.set_identifier_values(doi=old_doi, save=True)
    return pp


@pytest.fixture()
def preprint_with_v1_doi(provider):
    pp = PreprintFactory(provider=provider, is_published=True)
    v1_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp._id)
    pp.set_identifier_values(doi=v1_doi, save=True)
    return pp


class TestGetPreprrintsNeedingV1Doi:

    def test_includes_public_preprint_without_versioned_doi(self, preprint):
        qs = get_preprints_needing_v1_doi()
        assert preprint in qs

    def test_excludes_preprint_with_versioned_doi(self, preprint_with_v1_doi):
        qs = get_preprints_needing_v1_doi()
        assert preprint_with_v1_doi not in qs

    def test_excludes_preprint_with_no_doi_if_private(self, provider):
        private_preprint = PreprintFactory(provider=provider, is_published=False)
        private_preprint.is_public = False
        private_preprint.save()
        qs = get_preprints_needing_v1_doi()
        assert private_preprint not in qs

    def test_includes_withdrawn_preprint_with_ever_public(self, provider):
        pp = PreprintFactory(provider=provider, is_published=True)
        old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
        pp.set_identifier_values(doi=old_doi, save=True)
        pp.date_withdrawn = timezone.now()
        pp.ever_public = True
        pp.save()
        qs = get_preprints_needing_v1_doi()
        assert pp in qs

    def test_excludes_withdrawn_preprint_never_public(self, provider):
        pp = PreprintFactory(provider=provider, is_published=False)
        Preprint.objects.filter(pk=pp.pk).update(date_withdrawn=timezone.now())
        qs = get_preprints_needing_v1_doi()
        assert pp not in qs

    def test_excludes_version_2_preprint(self, preprint):
        from tests.utils import capture_notifications
        with capture_notifications():
            v2 = PreprintFactory.create_version(preprint, is_published=True, set_doi=False)
        old_doi = settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=v2.get_guid()._id)
        v2.set_identifier_values(doi=old_doi, save=True)
        qs = get_preprints_needing_v1_doi()
        assert v2 not in qs

    def test_excludes_qatest_tagged_preprint(self, preprint):
        preprint.add_system_tag('qatest')
        qs = get_preprints_needing_v1_doi()
        assert preprint not in qs

    def test_excludes_deleted_preprint(self, preprint):
        preprint.deleted = timezone.now()
        preprint.save()
        qs = get_preprints_needing_v1_doi()
        assert preprint not in qs

    def test_provider_filter_limits_results(self, preprint, provider):
        other_provider = PreprintProviderFactory()
        other_provider.doi_prefix = '10.12345'
        other_provider.save()
        other_preprint = PreprintFactory(provider=other_provider, is_published=True)
        old_doi = settings.DOI_FORMAT.format(prefix=other_provider.doi_prefix, guid=other_preprint.get_guid()._id)
        other_preprint.set_identifier_values(doi=old_doi, save=True)

        qs = get_preprints_needing_v1_doi(provider_id=provider._id)
        assert preprint in qs
        assert other_preprint not in qs

    def test_preprint_with_no_doi_identifier_is_included(self, provider):
        pp = PreprintFactory(provider=provider, is_published=True, set_doi=False)
        qs = get_preprints_needing_v1_doi()
        assert pp in qs

    def test_excludes_preprint_with_fresh_in_flight_marker(self, preprint):
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        qs = get_preprints_needing_v1_doi()
        assert preprint not in qs

    def test_includes_preprint_with_stale_in_flight_marker(self, preprint):
        stale_cutoff = timezone.now() - settings.PREPRINT_DOI_RESYNC_INFLIGHT_TIMEOUT
        preprint.doi_resync_queued_at = stale_cutoff - timedelta(minutes=1)
        preprint.save()
        qs = get_preprints_needing_v1_doi()
        assert preprint in qs


class TestResyncPreprintDoisV1:

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_dry_run_does_not_queue_tasks(self, mock_task, preprint):
        resync_preprint_dois_v1(dry_run=True)
        mock_task.apply_async.assert_not_called()

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_live_run_queues_task_for_each_preprint(self, mock_task, preprint):
        resync_preprint_dois_v1(dry_run=False)
        mock_task.apply_async.assert_called_once_with(kwargs={'preprint_id': preprint._id})

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_batch_size_limits_processed_count(self, mock_task, provider):
        preprints = []
        for _ in range(5):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)
            preprints.append(pp)

        resync_preprint_dois_v1(dry_run=False, batch_size=2)
        assert mock_task.apply_async.call_count == 2

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_skips_provider_without_doi_prefix(self, mock_task, provider):
        no_prefix_provider = PreprintProviderFactory()
        no_prefix_provider.doi_prefix = ''
        no_prefix_provider.save()
        pp = PreprintFactory(provider=no_prefix_provider, is_published=True)
        old_doi = '10.000/old-doi'
        pp.set_identifier_values(doi=old_doi, save=True)

        resync_preprint_dois_v1(dry_run=False)
        queued_ids = [
            call.kwargs['kwargs']['preprint_id']
            for call in mock_task.apply_async.call_args_list
        ]
        assert pp._id not in queued_ids

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_provider_filter_is_applied(self, mock_task, preprint, provider):
        other_provider = PreprintProviderFactory()
        other_provider.doi_prefix = '10.99999'
        other_provider.save()
        other_pp = PreprintFactory(provider=other_provider, is_published=True)
        old_doi = settings.DOI_FORMAT.format(prefix=other_provider.doi_prefix, guid=other_pp.get_guid()._id)
        other_pp.set_identifier_values(doi=old_doi, save=True)

        resync_preprint_dois_v1(dry_run=False, provider_id=provider._id)

        queued_ids = [
            call.kwargs['kwargs']['preprint_id']
            for call in mock_task.apply_async.call_args_list
        ]
        assert preprint._id in queued_ids
        assert other_pp._id not in queued_ids

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_already_versioned_doi_is_not_queued(self, mock_task, preprint_with_v1_doi):
        resync_preprint_dois_v1(dry_run=False)
        queued_ids = [
            call.kwargs['kwargs']['preprint_id']
            for call in mock_task.apply_async.call_args_list
        ]
        assert preprint_with_v1_doi._id not in queued_ids

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_queuing_marks_preprint_in_flight(self, mock_task, preprint):
        assert preprint.doi_resync_queued_at is None
        resync_preprint_dois_v1(dry_run=False)
        preprint.refresh_from_db()
        assert preprint.doi_resync_queued_at is not None

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_dry_run_does_not_mark_in_flight(self, mock_task, preprint):
        resync_preprint_dois_v1(dry_run=True)
        preprint.refresh_from_db()
        assert preprint.doi_resync_queued_at is None

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_capacity_limits_queued_count(self, mock_task, provider):
        for _ in range(5):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)

        result = resync_preprint_dois_v1(dry_run=False, batch_size=1000, capacity=2)
        assert mock_task.apply_async.call_count == 2
        assert result.queued == 2

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_zero_capacity_queues_nothing(self, mock_task, preprint):
        result = resync_preprint_dois_v1(dry_run=False, capacity=0)
        mock_task.apply_async.assert_not_called()
        assert result.queued == 0

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_in_flight_preprint_reduces_available_capacity(self, mock_task, provider):
        already_queued = PreprintFactory(provider=provider, is_published=True)
        old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=already_queued.get_guid()._id)
        already_queued.set_identifier_values(doi=old_doi, save=True)
        already_queued.doi_resync_queued_at = timezone.now()
        already_queued.save()

        needs_resync = PreprintFactory(provider=provider, is_published=True)
        old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=needs_resync.get_guid()._id)
        needs_resync.set_identifier_values(doi=old_doi, save=True)

        with mock.patch(
            'osf.management.commands.resync_preprint_dois_v1.settings.PREPRINT_DOI_RESYNC_MAX_IN_FLIGHT', 1
        ):
            result = resync_preprint_dois_v1(dry_run=False)

        mock_task.apply_async.assert_not_called()
        assert result.queued == 0


class TestResyncPreprintDoisV1Task:

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_reschedules_while_work_remains(self, mock_task, provider):
        for _ in range(3):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)

        with mock.patch.object(resync_preprint_dois_v1_task, 'apply_async') as mock_reschedule:
            resync_preprint_dois_v1_task(batch_size=1, dry_run=False)

        mock_reschedule.assert_called_once()
        assert mock_reschedule.call_args.kwargs['countdown'] == (
            settings.PREPRINT_DOI_RESYNC_DISPATCH_INTERVAL.total_seconds()
        )

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_does_not_reschedule_once_backlog_is_empty(self, mock_task, preprint):
        with mock.patch.object(resync_preprint_dois_v1_task, 'apply_async') as mock_reschedule:
            resync_preprint_dois_v1_task(batch_size=1000, dry_run=False)

        mock_reschedule.assert_not_called()

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_dry_run_never_reschedules(self, mock_task, provider):
        for _ in range(3):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)

        with mock.patch.object(resync_preprint_dois_v1_task, 'apply_async') as mock_reschedule:
            resync_preprint_dois_v1_task(batch_size=1, dry_run=True)

        mock_reschedule.assert_not_called()


class TestResyncPreprintDoisV1Command:

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.resync_preprint_dois_v1_task.apply_async')
    def test_live_run_starts_dispatcher_once(self, mock_apply_async, preprint):
        call_command('resync_preprint_dois_v1', batch_size=50, provider_id=preprint.provider._id)

        mock_apply_async.assert_called_once_with(
            kwargs={
                'batch_size': 50,
                'dry_run': False,
                'provider_id': preprint.provider._id,
            },
        )

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.resync_preprint_dois_v1_task.apply_async')
    def test_live_run_uses_default_options(self, mock_apply_async):
        call_command('resync_preprint_dois_v1')

        mock_apply_async.assert_called_once_with(
            kwargs={'batch_size': 1000, 'dry_run': False, 'provider_id': None},
        )

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    @mock.patch('osf.management.commands.resync_preprint_dois_v1.resync_preprint_dois_v1_task.apply_async')
    def test_live_run_does_not_dispatch_to_crossref_synchronously(self, mock_apply_async, mock_identifier_task, preprint):
        # handle() should hand off to the task rather than talking to Crossref itself
        call_command('resync_preprint_dois_v1')

        mock_identifier_task.apply_async.assert_not_called()

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.register_missing_unversioned_dois')
    @mock.patch('osf.management.commands.resync_preprint_dois_v1.resync_preprint_dois_v1')
    @mock.patch('osf.management.commands.resync_preprint_dois_v1.resync_preprint_dois_v1_task.apply_async')
    def test_dry_run_previews_both_passes_without_dispatching(
        self, mock_apply_async, mock_v1_pass, mock_unversioned_pass, preprint
    ):
        call_command('resync_preprint_dois_v1', dry_run=True, batch_size=25, provider_id=preprint.provider._id)

        mock_v1_pass.assert_called_once_with(dry_run=True, batch_size=25, provider_id=preprint.provider._id)
        mock_unversioned_pass.assert_called_once_with(dry_run=True, batch_size=25, provider_id=preprint.provider._id)
        mock_apply_async.assert_not_called()

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_dry_run_does_not_queue_or_mark_in_flight(self, mock_identifier_task, preprint):
        call_command('resync_preprint_dois_v1', dry_run=True)

        mock_identifier_task.apply_async.assert_not_called()
        preprint.refresh_from_db()
        assert preprint.doi_resync_queued_at is None
