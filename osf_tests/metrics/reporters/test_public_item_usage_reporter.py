from datetime import datetime, timedelta
from functools import cached_property
from operator import attrgetter
from unittest import mock

from django.test import TestCase
from elasticsearch_metrics.tests.util import RealElasticTestCase

from osf.metadata.rdfutils import OSF
from osf.metrics.events import OsfCountedUsageEvent
from osf.metrics.es8_metrics import (
    MonthlyPublicItemUsageReportEs8,
)
from osf.metrics.reporters.public_item_usage import PublicItemUsageReporter
from osf.metrics.utils import YearMonth
from osf_tests import factories
from ._testutils import list_monthly_reports


class TestPublicItemUsageReporter(RealElasticTestCase, TestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch('website.settings.DOMAIN', 'http://osf.example/'))

    @cached_property
    def item0(self):
        _item0 = factories.PreprintFactory(is_public=True, set_guid='item0')
        return _item0

    @cached_property
    def item1(self):
        _item1 = factories.ProjectFactory(is_public=True)
        _item1._id = 'item1'
        return _item1

    @cached_property
    def item2(self):
        _item2 = factories.ProjectFactory(is_public=True, parent=self.item1)
        _item2._id = 'item2'
        return _item2

    @cached_property
    def ym_empty(self) -> YearMonth:
        return YearMonth(2012, 7)

    @cached_property
    def ym_sparse(self) -> YearMonth:
        return YearMonth(2017, 7)

    @cached_property
    def ym_busy(self) -> YearMonth:
        return YearMonth(2023, 7)

    def _setup_sparse_month_usage(self):
        # "sparse" month:
        #   item0: 3 views, 0 downloads, 2 sessions
        #   item1: 1 views, 1 download, 1 session (plus 1 view from child item2)
        #   item2: 1 views, 0 downloads, 1 session
        _month_start = self.ym_sparse.month_start()
        _save_usage(
            self.item0,
            timestamp=_month_start,
            sessionhour_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            self.item0,
            timestamp=_month_start + timedelta(minutes=2),
            sessionhour_id='sesh0',
            action_labels=['view'],
        )
        _save_usage(
            self.item1,
            timestamp=_month_start + timedelta(minutes=3),
            sessionhour_id='sesh0',
            action_labels=['download'],
        )
        _save_usage(
            self.item0,
            timestamp=_month_start + timedelta(days=17),
            sessionhour_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            self.item1,
            timestamp=_month_start + timedelta(days=17, minutes=3),
            sessionhour_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            self.item2,
            timestamp=_month_start + timedelta(days=17, minutes=5),
            sessionhour_id='sesh1',
            action_labels=['view'],
        )
        _save_usage(
            self.item2,
            timestamp=_month_start + timedelta(days=17, minutes=11),
            sessionhour_id='sesh1',
            action_labels=['download'],
        )

    def _setup_busy_month_item0(self):
        # item0: 4 sessions, 4*7 views, 4*5 downloads
        _month_start = self.ym_busy.month_start()
        for _sesh in range(0, 4):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 7):
                _save_usage(
                    self.item0,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    sessionhour_id=f'sesh0{_sesh}',
                    action_labels=['view'],
                )
            for _minute in range(10, 15):
                _save_usage(
                    self.item0,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    sessionhour_id=f'sesh0{_sesh}',
                    action_labels=['download'],
                )
        # plus prior report with cumulative counts:
        # 4 views, 3 view sessions, 2 downloads, 1 download session
        MonthlyPublicItemUsageReportEs8.record(
            report_yearmonth=self.ym_busy.prior(),
            item_iri='http://osf.example/item0_v1',
            item_osfids=['item0_v1'],
            item_types=[OSF.Preprint],
            platform_iris=['http://osf.example/'],
            database_iris=[self.item0.provider.get_semantic_iri()],
            provider_ids=[self.item0.provider._id],
            view_count=1,
            view_session_count=1,
            cumulative_view_count=4,
            cumulative_view_session_count=3,
            download_count=2,
            download_session_count=1,
            cumulative_download_count=2,
            cumulative_download_session_count=1,
        )

    def _setup_busy_month_item1(self):
        # item1: 10 sessions, 6*9 views, 5*7 downloads
        # (plus 11 views in 11 sessions from child item2)
        _month_start = self.ym_busy.month_start()
        for _sesh in range(0, 6):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(0, 9):
                _save_usage(
                    self.item1,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    sessionhour_id=f'sesh1{_sesh}',
                    action_labels=['view'],
                )
        for _sesh in range(5, 10):
            _sesh_start = _month_start + timedelta(days=_sesh)
            for _minute in range(10, 17):
                _save_usage(
                    self.item1,
                    timestamp=_sesh_start + timedelta(minutes=_minute),
                    sessionhour_id=f'sesh1{_sesh}',
                    action_labels=['download'],
                )

    def _setup_busy_month_item2(self):
        # item2: 11 sessions, 11 views, 11 downloads (child of item1)
        _month_start = self.ym_busy.month_start()
        for _sesh in range(1, 12):
            _save_usage(
                self.item2,
                timestamp=_month_start + timedelta(days=_sesh),
                sessionhour_id=f'sesh2{_sesh}',
                action_labels=['view'],
            )
            _save_usage(
                self.item2,
                timestamp=_month_start + timedelta(days=_sesh, hours=_sesh),
                sessionhour_id=f'sesh2{_sesh}',
                action_labels=['download'],
            )

    def test_no_data(self):
        _reporter = PublicItemUsageReporter(self.ym_empty)
        _empty = list_monthly_reports(_reporter)
        assert _empty == []

    def test_reporter(self):
        self._setup_sparse_month_usage()
        self._setup_busy_month_item0()
        self._setup_busy_month_item1()
        self._setup_busy_month_item2()
        OsfCountedUsageEvent.refresh()

        _empty = list_monthly_reports(PublicItemUsageReporter(self.ym_empty))
        _sparse = list_monthly_reports(PublicItemUsageReporter(self.ym_sparse))
        _busy = list_monthly_reports(PublicItemUsageReporter(self.ym_busy))

        # empty month:
        assert _empty == []

        # sparse month:
        assert len(_sparse) == 3
        _sparse_item0, _sparse_item1, _sparse_item2 = sorted(_sparse, key=attrgetter('item_iri'))
        # sparse-month item0
        assert isinstance(_sparse_item0, MonthlyPublicItemUsageReportEs8)
        assert _sparse_item0.item_iri == 'http://osf.example/item0_v1'
        assert _sparse_item0.item_osfids == ['item0_v1']
        assert _sparse_item0.provider_ids == [self.item0.provider._id]
        assert _sparse_item0.platform_iris == ['http://osf.example']
        assert _sparse_item0.view_count == 3
        assert _sparse_item0.view_session_count == 2
        assert _sparse_item0.download_count == 0
        assert _sparse_item0.download_session_count == 0
        assert _sparse_item0.cumulative_view_count == 3
        assert _sparse_item0.cumulative_view_session_count == 2
        assert _sparse_item0.cumulative_download_count == 0
        assert _sparse_item0.cumulative_download_session_count == 0
        # sparse-month item1
        assert isinstance(_sparse_item1, MonthlyPublicItemUsageReportEs8)
        assert _sparse_item1.item_iri == 'http://osf.example/item1'
        assert _sparse_item1.item_osfids == ['item1']
        assert _sparse_item1.provider_ids == ['osf']
        assert _sparse_item1.platform_iris == ['http://osf.example']
        assert _sparse_item1.view_count == 2  # including item2
        assert _sparse_item1.view_session_count == 1  # including item2
        assert _sparse_item1.download_count == 1  # NOT including item2
        assert _sparse_item1.download_session_count == 1  # NOT including item2
        assert _sparse_item1.cumulative_view_count == 2
        assert _sparse_item1.cumulative_view_session_count == 1
        assert _sparse_item1.cumulative_download_count == 1
        assert _sparse_item1.cumulative_download_session_count == 1
        # sparse-month item2
        assert isinstance(_sparse_item1, MonthlyPublicItemUsageReportEs8)
        assert _sparse_item2.item_iri == 'http://osf.example/item2'
        assert _sparse_item2.item_osfids == ['item2']
        assert _sparse_item2.provider_ids == ['osf']
        assert _sparse_item2.platform_iris == ['http://osf.example']
        assert _sparse_item2.view_count == 1
        assert _sparse_item2.view_session_count == 1
        assert _sparse_item2.download_count == 1
        assert _sparse_item2.download_session_count == 1
        assert _sparse_item2.cumulative_view_count == 1
        assert _sparse_item2.cumulative_view_session_count == 1
        assert _sparse_item2.cumulative_download_count == 1
        assert _sparse_item2.cumulative_download_session_count == 1

        # busy month:
        assert len(_busy) == 3
        _busy_item0, _busy_item1, _busy_item2 = sorted(_busy, key=attrgetter('item_iri'))
        # busy-month item0 (plus prior-month report)
        assert isinstance(_busy_item0, MonthlyPublicItemUsageReportEs8)
        assert _busy_item0.item_iri == 'http://osf.example/item0_v1'
        assert _busy_item0.item_osfids == ['item0_v1']
        assert _busy_item0.provider_ids == [self.item0.provider._id]
        assert _busy_item0.platform_iris == ['http://osf.example']
        assert _busy_item0.view_count == 4 * 7
        assert _busy_item0.view_session_count == 4
        assert _busy_item0.download_count == 4 * 5
        assert _busy_item0.download_session_count == 4
        # plus values from prior report:
        assert _busy_item0.cumulative_view_count == (4 * 7) + 4
        assert _busy_item0.cumulative_view_session_count == 4 + 3
        assert _busy_item0.cumulative_download_count == (4 * 5) + 2
        assert _busy_item0.cumulative_download_session_count == 4 + 1
        # busy-month item1
        assert isinstance(_busy_item1, MonthlyPublicItemUsageReportEs8)
        assert _busy_item1.item_iri == 'http://osf.example/item1'
        assert _busy_item1.item_osfids == ['item1']
        assert _busy_item1.provider_ids == ['osf']
        assert _busy_item1.platform_iris == ['http://osf.example']
        assert _busy_item1.view_count == 6 * 9 + 11
        assert _busy_item1.view_session_count == 6 + 11
        assert _busy_item1.download_count == 5 * 7
        assert _busy_item1.download_session_count == 5
        assert _busy_item1.cumulative_view_count == 6 * 9 + 11
        assert _busy_item1.cumulative_view_session_count == 6 + 11
        assert _busy_item1.cumulative_download_count == 5 * 7
        assert _busy_item1.cumulative_download_session_count == 5
        # busy-month item2
        assert isinstance(_busy_item2, MonthlyPublicItemUsageReportEs8)
        assert _busy_item2.item_iri == 'http://osf.example/item2'
        assert _busy_item2.item_osfids == ['item2']
        assert _busy_item2.provider_ids == ['osf']
        assert _busy_item2.platform_iris == ['http://osf.example']
        assert _busy_item2.view_count == 11
        assert _busy_item2.view_session_count == 11
        assert _busy_item2.download_count == 11
        assert _busy_item2.download_session_count == 11
        assert _busy_item2.cumulative_view_count == 11
        assert _busy_item2.cumulative_view_session_count == 11
        assert _busy_item2.cumulative_download_count == 11
        assert _busy_item2.cumulative_download_session_count == 11


def _save_usage(
    item,
    *,
    timestamp: datetime,
    action_labels: list[str],
    **kwargs,
):
    _countedusage_kwargs = {
        'timestamp': timestamp,
        'item_osfid': item._id,
        'action_labels': action_labels,
        'platform_iri': 'http://osf.example',
        **kwargs,
    }
    OsfCountedUsageEvent.record(**_countedusage_kwargs)
