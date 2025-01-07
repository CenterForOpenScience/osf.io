from datetime import datetime, timedelta
from operator import attrgetter
from unittest import mock

import pytest

from osf.metrics.counted_usage import CountedAuthUsage
from osf.metrics.preprint_metrics import (
    PreprintDownload,
    PreprintView,
)
from osf.metrics.reporters.public_item_usage import PublicItemUsageReporter
from osf.metrics.reports import PublicItemUsageReport
from osf.metrics.utils import YearMonth
from osf import models as osfdb
from osf_tests import factories
from ._testutils import list_monthly_reports


@pytest.mark.es_metrics
@pytest.mark.django_db
class TestPublicItemUsageReporter:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with mock.patch('website.settings.DOMAIN', 'http://osf.example'):
            yield

    @pytest.fixture
    def item0(self):
        _item0 = factories.PreprintFactory(is_public=True)
        guid = _item0.get_guid()
        guid._id = 'item0'
        guid.save()

        _item0._id = None
        return _item0

    @pytest.fixture
    def item1(self):
        _item1 = factories.ProjectFactory(is_public=True)
        _item1._id = 'item1'
        return _item1

    @pytest.fixture
    def item2(self, item1):
        _item2 = factories.ProjectFactory(is_public=True, parent=item1)
        _item2._id = 'item2'
        return _item2

    @pytest.fixture
    def ym_empty(self) -> YearMonth:
        return YearMonth(2012, 7)

    @pytest.fixture
    def ym_sparse(self) -> YearMonth:
        return YearMonth(2017, 7)

    @pytest.fixture
    def ym_busy(self) -> YearMonth:
        return YearMonth(2023, 7)

    @pytest.fixture
    def sparse_month_usage(self, ym_sparse, item0, item1, item2):
        # "sparse" month:
        #   item0: 3 views, 0 downloads, 2 sessions
        #   item1: 1 views, 1 download, 1 session (plus 1 view from child item2)
        #   item2: 1 views, 0 downloads, 1 session
        _month_start = ym_sparse.month_start()
        _save_usage(
            item0,
            timestamp=_month_start,
            session_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            item0,
            timestamp=_month_start + timedelta(minutes=2),
            session_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            item1,
            timestamp=_month_start + timedelta(minutes=3),
            session_id='sesh0',
            action_labels=['download'],
        )
        _save_usage(
            item0,
            timestamp=_month_start + timedelta(days=17),
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            item1,
            timestamp=_month_start + timedelta(days=17, minutes=3),
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            item2,
            timestamp=_month_start + timedelta(days=17, minutes=5),
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            item2,
            timestamp=_month_start + timedelta(days=17, minutes=11),
            session_id='sesh1',
            action_labels=['download'],
        )

    @pytest.fixture
    def busy_month_item0(self, ym_busy, item0):
        # item0: 4 sessions, 4*7 views, 4*5 downloads
        _month_start = ym_busy.month_start()
        for _sesh in range(0, 4):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 7):
                _save_usage(
                    item0,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    session_id=f'sesh0{_sesh}',
                    action_labels=['view'],
                )
            for _minute in range(10, 15):
                _save_usage(
                    item0,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    session_id=f'sesh0{_sesh}',
                    action_labels=['download'],
                )

    @pytest.fixture
    def busy_month_item1(self, ym_busy, item1):
        # item1: 10 sessions, 6*9 views, 5*7 downloads
        # (plus 11 views in 11 sessions from child item2)
        _month_start = ym_busy.month_start()
        for _sesh in range(0, 6):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 9):
                _save_usage(
                    item1,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    session_id=f'sesh1{_sesh}',
                    action_labels=['view'],
                )
        for _sesh in range(5, 10):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(10, 17):
                _save_usage(
                    item1,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    session_id=f'sesh1{_sesh}',
                    action_labels=['download'],
                )

    @pytest.fixture
    def busy_month_item2(self, ym_busy, item2):
        # item2: 11 sessions, 11 views, 11 downloads (child of item1)
        _month_start = ym_busy.month_start()
        for _sesh in range(1, 12):
            _save_usage(
                item2,
                timestamp=_month_start + timedelta(days=_sesh),
                session_id=f'sesh2{_sesh}',
                action_labels=['view'],
            )
            _save_usage(
                item2,
                timestamp=_month_start + timedelta(days=_sesh, hours=_sesh),
                session_id=f'sesh2{_sesh}',
                action_labels=['download'],
            )

    def test_no_data(self, ym_empty):
        _reporter = PublicItemUsageReporter(ym_empty)
        _empty = list_monthly_reports(_reporter)
        assert _empty == []

    def test_reporter(self, ym_empty, ym_sparse, ym_busy, sparse_month_usage, busy_month_item0, busy_month_item1, busy_month_item2, item0):
        _empty = list_monthly_reports(PublicItemUsageReporter(ym_empty))
        _sparse = list_monthly_reports(PublicItemUsageReporter(ym_sparse))
        _busy = list_monthly_reports(PublicItemUsageReporter(ym_busy))

        # empty month:
        assert _empty == []

        # sparse month:
        assert len(_sparse) == 3
        _sparse_item0, _sparse_item1, _sparse_item2 = sorted(_sparse, key=attrgetter('item_osfid'))
        # sparse-month item0
        assert isinstance(_sparse_item0, PublicItemUsageReport)
        assert _sparse_item0.item_osfid == 'item0_v1'
        assert _sparse_item0.provider_id == [item0.provider._id]
        assert _sparse_item0.platform_iri == ['http://osf.example']
        assert _sparse_item0.view_count == 3
        assert _sparse_item0.view_session_count is None  # no session count for preprints
        assert _sparse_item0.download_count == 0
        assert _sparse_item0.download_session_count is None  # no session count for preprints
        # sparse-month item1
        assert isinstance(_sparse_item1, PublicItemUsageReport)
        assert _sparse_item1.item_osfid == 'item1'
        assert _sparse_item1.provider_id == ['osf']
        assert _sparse_item1.platform_iri == ['http://osf.example']
        assert _sparse_item1.view_count == 2  # including item2
        assert _sparse_item1.view_session_count == 1  # including item2
        assert _sparse_item1.download_count == 1  # NOT including item2
        assert _sparse_item1.download_session_count == 1  # NOT including item2
        # sparse-month item2
        assert isinstance(_sparse_item1, PublicItemUsageReport)
        assert _sparse_item2.item_osfid == 'item2'
        assert _sparse_item2.provider_id == ['osf']
        assert _sparse_item2.platform_iri == ['http://osf.example']
        assert _sparse_item2.view_count == 1
        assert _sparse_item2.view_session_count == 1
        assert _sparse_item2.download_count == 1
        assert _sparse_item2.download_session_count == 1

        # busy month:
        assert len(_busy) == 3
        _busy_item0, _busy_item1, _busy_item2 = sorted(_busy, key=attrgetter('item_osfid'))
        # busy-month item0
        assert isinstance(_busy_item0, PublicItemUsageReport)
        assert _busy_item0.item_osfid == 'item0_v1'
        assert _busy_item0.provider_id == [item0.provider._id]
        assert _busy_item0.platform_iri == ['http://osf.example']
        assert _busy_item0.view_count == 4 * 7
        assert _busy_item0.view_session_count is None  # no session count for preprints
        assert _busy_item0.download_count == 4 * 5
        assert _busy_item0.download_session_count is None  # no session count for preprints
        # busy-month item1
        assert isinstance(_busy_item1, PublicItemUsageReport)
        assert _busy_item1.item_osfid == 'item1'
        assert _busy_item1.provider_id == ['osf']
        assert _busy_item1.platform_iri == ['http://osf.example']
        assert _busy_item1.view_count == 6 * 9 + 11
        assert _busy_item1.view_session_count == 6 + 11
        assert _busy_item1.download_count == 5 * 7
        assert _busy_item1.download_session_count == 5
        # busy-month item2
        assert isinstance(_busy_item2, PublicItemUsageReport)
        assert _busy_item2.item_osfid == 'item2'
        assert _busy_item2.provider_id == ['osf']
        assert _busy_item2.platform_iri == ['http://osf.example']
        assert _busy_item2.view_count == 11
        assert _busy_item2.view_session_count == 11
        assert _busy_item2.download_count == 11
        assert _busy_item2.download_session_count == 11


def _save_usage(
    item,
    *,
    timestamp: datetime,
    action_labels: list[str],
    **kwargs,
):
    _countedusage_kwargs = {
        'timestamp': timestamp,
        'item_guid': item._id,
        'action_labels': action_labels,
        'platform_iri': 'http://osf.example',
        **kwargs,
    }
    CountedAuthUsage(**_countedusage_kwargs).save(refresh=True)
    if isinstance(item, osfdb.Preprint):
        if 'view' in action_labels:
            _save_preprint_view(item, timestamp)
        if 'download' in action_labels:
            _save_preprint_download(item, timestamp)


def _save_preprint_view(preprint, timestamp):
    PreprintView(
        timestamp=timestamp,
        count=1,
        preprint_id=preprint._id,
        provider_id=preprint.provider._id,
    ).save(refresh=True)


def _save_preprint_download(preprint, timestamp):
    PreprintDownload(
        timestamp=timestamp,
        count=1,
        preprint_id=preprint._id,
        provider_id=preprint.provider._id,
    ).save(refresh=True)
