import pytest

from datetime import timedelta
from django.utils import timezone

from osf_tests.factories import ScheduledBannerFactory

@pytest.mark.django_db
class TestPreprintDetail:

    @pytest.fixture
    def date(self):
        return timezone.now()

    @pytest.fixture()
    def banner(self):
        return ScheduledBannerFactory()

    @pytest.fixture()
    def tomorrow_banner(self, date):
        return ScheduledBannerFactory(
            start_date=date + timedelta(days=1)
        )

    @pytest.fixture()
    def yesterday_banner(self, date):
        return ScheduledBannerFactory(
            start_date=date - timedelta(days=1)
        )

    @pytest.fixture()
    def url(self):
        return '/_/banners/current/'

    @pytest.fixture()
    def res(self, app, url):
        return app.get(url)

    @pytest.fixture()
    def data(self, res):
        return res.json['data']

    def test_banner_detail(self, banner, res, data):
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert data['type'] == 'banners'

    # When there's no current banner endpoint returns dummy ScheduledBanner with no data
    def test_no_current_banner(self, tomorrow_banner, yesterday_banner, data):
        assert not data.get('start_date')
