from datetime import timedelta
from operator import attrgetter
from unittest import mock

import pytest

from osf.metrics.counted_usage import CountedAuthUsage
from osf.metrics.reporters.public_item_usage import PublicItemUsageReporter
from osf.metrics.reports import PublicItemUsageReport
from osf.metrics.utils import YearMonth


@pytest.mark.es_metrics
class TestPublicItemUsageReporter:
    @pytest.fixture(autouse=True)
    def _mocks(self):
        with (
            # set a tiny page size to force aggregation pagination:
            mock.patch('osf.metrics.reporters.public_item_usage._CHUNK_SIZE', 1),
            # HACK: skip auto-filling fields from the database:
            mock.patch('osf.models.base.Guid.load', return_value=None),
        ):
            yield

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
    def sparse_month_usage(self, ym_sparse):
        # "sparse" month:
        #   item0: 3 views, 0 downloads, 2 sessions
        #   item1: 1 views, 1 download, 1 session (plus 1 view from child item2)
        #   item2: 1 views, 0 downloads, 1 session
        _month_start = ym_sparse.target_month()
        _save_usage(
            timestamp=_month_start,
            item_guid='item0',
            session_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(minutes=2),
            item_guid='item0',
            session_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(minutes=3),
            item_guid='item1',
            session_id='sesh0',
            action_labels=['download'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(days=17),
            item_guid='item0',
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(days=17, minutes=3),
            item_guid='item1',
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(days=17, minutes=5),
            item_guid='item2',
            surrounding_guids=['item1'],
            session_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            timestamp=_month_start + timedelta(days=17, minutes=11),
            item_guid='item2',
            surrounding_guids=['item1'],
            session_id='sesh1',
            action_labels=['download'],
        )

    @pytest.fixture
    def busy_month_item0(self, ym_busy):
        # item0: 4 sessions, 4*7 views, 4*5 downloads
        _month_start = ym_busy.target_month()
        for _sesh in range(0, 4):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 7):
                _save_usage(
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    item_guid='item0',
                    session_id=f'sesh0{_sesh}',
                    action_labels=['view'],
                )
            for _minute in range(10, 15):
                _save_usage(
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    item_guid='item0',
                    session_id=f'sesh0{_sesh}',
                    action_labels=['download'],
                )

    @pytest.fixture
    def busy_month_item1(self, ym_busy):
        # item1: 10 sessions, 6*9 views, 5*7 downloads, 2 providers
        # (plus 11 views in 11 sessions from child item2)
        _month_start = ym_busy.target_month()
        for _sesh in range(0, 6):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 9):
                _save_usage(
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    item_guid='item1',
                    session_id=f'sesh1{_sesh}',
                    action_labels=['view'],
                )
        for _sesh in range(5, 10):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(10, 17):
                _save_usage(
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    item_guid='item1',
                    session_id=f'sesh1{_sesh}',
                    action_labels=['download'],
                    provider_id='prov1',  # additional provider_id
                )

    @pytest.fixture
    def busy_month_item2(self, ym_busy):
        # item2: 11 sessions, 11 views, 11 downloads (child of item1)
        _month_start = ym_busy.target_month()
        for _sesh in range(1, 12):
            _save_usage(
                timestamp=_month_start + timedelta(days=_sesh),
                item_guid='item2',
                surrounding_guids=['item1'],
                session_id=f'sesh2{_sesh}',
                action_labels=['view'],
            )
            _save_usage(
                timestamp=_month_start + timedelta(days=_sesh, hours=_sesh),
                item_guid='item2',
                surrounding_guids=['item1'],
                session_id=f'sesh2{_sesh}',
                action_labels=['download'],
            )

    def test_reporter(self, ym_empty, ym_sparse, ym_busy, sparse_month_usage, busy_month_item0, busy_month_item1, busy_month_item2):
        _reporter = PublicItemUsageReporter()
        _empty = list(_reporter.report(ym_empty))
        _sparse = list(_reporter.report(ym_sparse))
        _busy = list(_reporter.report(ym_busy))

        # empty month:
        assert _empty == []

        # sparse month:
        assert len(_sparse) == 3
        _sparse_item0, _sparse_item1, _sparse_item2 = sorted(_sparse, key=attrgetter('item_osfid'))
        # sparse-month item0
        assert isinstance(_sparse_item0, PublicItemUsageReport)
        assert _sparse_item0.item_osfid == 'item0'
        assert _sparse_item0.provider_id == ['prov0']
        assert _sparse_item0.platform_iri == ['http://osf.example']
        assert _sparse_item0.view_count == 3
        assert _sparse_item0.view_session_count == 2
        assert _sparse_item0.download_count == 0
        assert _sparse_item0.download_session_count == 0
        # sparse-month item1
        assert isinstance(_sparse_item1, PublicItemUsageReport)
        assert _sparse_item1.item_osfid == 'item1'
        assert _sparse_item1.provider_id == ['prov0']
        assert _sparse_item1.platform_iri == ['http://osf.example']
        assert _sparse_item1.view_count == 2  # including item2
        assert _sparse_item1.view_session_count == 1  # including item2
        assert _sparse_item1.download_count == 1  # NOT including item2
        assert _sparse_item1.download_session_count == 1  # NOT including item2
        # sparse-month item2
        assert isinstance(_sparse_item1, PublicItemUsageReport)
        assert _sparse_item2.item_osfid == 'item2'
        assert _sparse_item2.provider_id == ['prov0']
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
        assert _busy_item0.item_osfid == 'item0'
        assert _busy_item0.provider_id == ['prov0']
        assert _busy_item0.platform_iri == ['http://osf.example']
        assert _busy_item0.view_count == 4 * 7
        assert _busy_item0.view_session_count == 4
        assert _busy_item0.download_count == 4 * 5
        assert _busy_item0.download_session_count == 4
        # busy-month item1
        assert isinstance(_busy_item1, PublicItemUsageReport)
        assert _busy_item1.item_osfid == 'item1'
        assert _busy_item1.provider_id == ['prov0', 'prov1']
        assert _busy_item1.platform_iri == ['http://osf.example']
        assert _busy_item1.view_count == 6 * 9 + 11
        assert _busy_item1.view_session_count == 6 + 11
        assert _busy_item1.download_count == 5 * 7
        assert _busy_item1.download_session_count == 5
        # busy-month item2
        assert isinstance(_busy_item2, PublicItemUsageReport)
        assert _busy_item2.item_osfid == 'item2'
        assert _busy_item2.provider_id == ['prov0']
        assert _busy_item2.platform_iri == ['http://osf.example']
        assert _busy_item2.view_count == 11
        assert _busy_item2.view_session_count == 11
        assert _busy_item2.download_count == 11
        assert _busy_item2.download_session_count == 11


def _save_usage(**kwargs):
    _kwargs = {  # overridable defaults:
        'platform_iri': 'http://osf.example',
        'item_public': True,
        'provider_id': 'prov0',
        **kwargs,
    }
    CountedAuthUsage(**_kwargs).save(refresh=True)
