import pytest
from unittest import mock
from django.utils import timezone

from osf.models import Preprint
from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.management.commands.resync_preprint_dois_v1 import (
    get_preprints_needing_v1_doi,
    resync_preprint_dois_v1,
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


class TestResyncPreprintDoisV1:

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_dry_run_does_not_queue_tasks(self, mock_task, preprint):
        resync_preprint_dois_v1(dry_run=True)
        mock_task.apply_async.assert_not_called()

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_live_run_queues_task_for_each_preprint(self, mock_task, preprint):
        resync_preprint_dois_v1(dry_run=False, rate_limit=0)
        mock_task.apply_async.assert_called_once_with(kwargs={'preprint_id': preprint._id})

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_batch_size_limits_processed_count(self, mock_task, provider):
        preprints = []
        for _ in range(5):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)
            preprints.append(pp)

        resync_preprint_dois_v1(dry_run=False, batch_size=2, rate_limit=0)
        assert mock_task.apply_async.call_count == 2

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_skips_provider_without_doi_prefix(self, mock_task, provider):
        no_prefix_provider = PreprintProviderFactory()
        no_prefix_provider.doi_prefix = ''
        no_prefix_provider.save()
        pp = PreprintFactory(provider=no_prefix_provider, is_published=True)
        old_doi = '10.000/old-doi'
        pp.set_identifier_values(doi=old_doi, save=True)

        resync_preprint_dois_v1(dry_run=False, rate_limit=0)
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

        resync_preprint_dois_v1(dry_run=False, rate_limit=0, provider_id=provider._id)

        queued_ids = [
            call.kwargs['kwargs']['preprint_id']
            for call in mock_task.apply_async.call_args_list
        ]
        assert preprint._id in queued_ids
        assert other_pp._id not in queued_ids

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_already_versioned_doi_is_not_queued(self, mock_task, preprint_with_v1_doi):
        resync_preprint_dois_v1(dry_run=False, rate_limit=0)
        queued_ids = [
            call.kwargs['kwargs']['preprint_id']
            for call in mock_task.apply_async.call_args_list
        ]
        assert preprint_with_v1_doi._id not in queued_ids

    @mock.patch('osf.management.commands.resync_preprint_dois_v1.time.sleep')
    @mock.patch('osf.management.commands.resync_preprint_dois_v1.async_request_identifier_update')
    def test_rate_limit_triggers_sleep(self, mock_task, mock_sleep, provider):
        for _ in range(3):
            pp = PreprintFactory(provider=provider, is_published=True)
            old_doi = settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=pp.get_guid()._id)
            pp.set_identifier_values(doi=old_doi, save=True)

        resync_preprint_dois_v1(dry_run=False, rate_limit=2)
        mock_sleep.assert_called_once()
