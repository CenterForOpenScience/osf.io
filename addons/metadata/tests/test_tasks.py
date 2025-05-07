import mock
from datetime import datetime

from nose.tools import assert_false, assert_equal, assert_raises

from addons.metadata import tasks as metadata_tasks


def _patch_kaken_settings():
    return mock.patch.multiple(
        metadata_tasks.settings,
        KAKEN_ELASTIC_URI='http://localhost:9200',
        KAKEN_RESOURCESYNC_URL='https://nrid.example/sync',
        KAKEN_ELASTIC_INDEX='kaken-test',
        KAKEN_ELASTIC_ANALYZER_CONFIG={},
        KAKEN_ELASTIC_KWARGS={},
    )


@mock.patch('website.app.init_app')
@mock.patch('addons.metadata.tasks.logger')
def test_sync_kaken_data_skips_when_disabled(mock_logger, mock_init_app):
    with mock.patch.object(metadata_tasks.settings, 'KAKEN_ELASTIC_URI', None):
        metadata_tasks.sync_kaken_data.run()

    mock_logger.info.assert_called_with('KAKEN functionality disabled (KAKEN_ELASTIC_URI is None), skipping sync')
    assert_false(mock_init_app.called)


@mock.patch('addons.metadata.suggestions.kaken.client.ResourceSyncClient')
@mock.patch('addons.metadata.suggestions.kaken.transformer.KakenToElasticsearchTransformer')
@mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService')
@mock.patch('scripts.update_kaken.sync_kaken_data', return_value=True)
@mock.patch('website.app.init_app')
def test_sync_kaken_data_starts_incremental_sync(mock_init_app, mock_do_sync, mock_es_cls, mock_transformer_cls, mock_client_cls):
    es_instance = mock.MagicMock()
    es_instance.index_exists.return_value = True
    mock_es_cls.return_value = es_instance

    sync_log = mock.MagicMock()
    last_success = mock.MagicMock()
    last_success.completed_at = '2025-09-22T00:00:00Z'

    with _patch_kaken_settings(), \
            mock.patch('addons.metadata.models.KakenSyncLog') as mock_sync_log:
        mock_sync_log.get_last_sync_log.return_value = None
        mock_sync_log.get_last_successful_sync.return_value = last_success
        mock_sync_log.start_sync.return_value = sync_log

        metadata_tasks.sync_kaken_data.run()

        mock_sync_log.start_sync.assert_called_once_with(sync_type='incremental')
        mock_do_sync.assert_called_once()
        args, kwargs = mock_do_sync.call_args
        assert_equal(kwargs.get('dry_run'), False)


@mock.patch('addons.metadata.suggestions.kaken.client.ResourceSyncClient')
@mock.patch('addons.metadata.suggestions.kaken.transformer.KakenToElasticsearchTransformer')
@mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService')
@mock.patch('scripts.update_kaken.sync_kaken_data', return_value=True)
@mock.patch('website.app.init_app')
def test_sync_kaken_data_resumes_incomplete_log(mock_init_app, mock_do_sync, mock_es_cls, mock_transformer_cls, mock_client_cls):
    es_instance = mock.MagicMock()
    es_instance.index_exists.return_value = True
    mock_es_cls.return_value = es_instance

    incomplete_log = mock.MagicMock()
    incomplete_log.status = 'in_progress'

    with _patch_kaken_settings(), \
            mock.patch('addons.metadata.models.KakenSyncLog') as mock_sync_log:
        mock_sync_log.get_last_sync_log.return_value = incomplete_log

        metadata_tasks.sync_kaken_data.run()

        assert_false(mock_sync_log.start_sync.called)
        assert_false(mock_sync_log.get_last_successful_sync.called)
        mock_do_sync.assert_called_once()


@mock.patch('addons.metadata.suggestions.kaken.client.ResourceSyncClient')
@mock.patch('addons.metadata.suggestions.kaken.transformer.KakenToElasticsearchTransformer')
@mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService')
@mock.patch('scripts.update_kaken.sync_kaken_data', return_value=False)
@mock.patch('website.app.init_app')
def test_sync_kaken_data_raises_on_failure(mock_init_app, mock_do_sync, mock_es_cls, mock_transformer_cls, mock_client_cls):
    es_instance = mock.MagicMock()
    es_instance.index_exists.return_value = True
    mock_es_cls.return_value = es_instance

    sync_log = mock.MagicMock()

    with _patch_kaken_settings(), \
            mock.patch('addons.metadata.models.KakenSyncLog') as mock_sync_log:
        mock_sync_log.get_last_sync_log.return_value = None
        mock_sync_log.get_last_successful_sync.return_value = None
        mock_sync_log.start_sync.return_value = sync_log

        assert_raises(Exception, metadata_tasks.sync_kaken_data.run)


@mock.patch('addons.metadata.tasks.logger')
@mock.patch('website.app.init_app')
def test_cleanup_old_sync_logs_deletes_expected(mock_init_app, mock_logger):
    now = datetime(2025, 9, 23, 0, 0, 0)
    keep_entries = [mock.MagicMock(id=i) for i in range(3)]

    completed_qs = mock.MagicMock()
    ordered_qs = mock.MagicMock()
    ordered_qs.__getitem__.return_value = keep_entries
    completed_qs.order_by.return_value = ordered_qs

    delete_qs = mock.MagicMock()
    exclude_qs = mock.MagicMock()
    exclude_qs.delete.return_value = (5, {})
    delete_qs.exclude.return_value = exclude_qs

    with mock.patch.object(metadata_tasks, 'timezone') as mock_timezone, \
            mock.patch('addons.metadata.models.KakenSyncLog') as mock_sync_log:
        mock_timezone.now.return_value = now
        mock_sync_log.objects.filter.side_effect = [completed_qs, delete_qs]

        metadata_tasks.cleanup_old_sync_logs()

        cutoff = now - metadata_tasks.timedelta(days=30)
        expected_keep_ids = [e.id for e in keep_entries]

        mock_sync_log.objects.filter.assert_any_call(status='completed')
        mock_sync_log.objects.filter.assert_any_call(started_at__lt=cutoff)
        delete_qs.exclude.assert_called_once_with(id__in=expected_keep_ids)
        exclude_qs.delete.assert_called_once()
        mock_logger.info.assert_called_with('Deleted 5 old KAKEN sync logs')
