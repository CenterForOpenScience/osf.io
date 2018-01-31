import pytest

from datetime import timedelta
from django.utils import timezone
from osf.exceptions import ValidationValueError
from osf_tests.factories import ScheduledBannerFactory

@pytest.mark.django_db
class TestScheduledBanner:

    @pytest.fixture
    def date(self):
        # So that in a single run tests all use the same base time
        return timezone.now()

    @pytest.fixture
    def current_banner(self, date):
        return ScheduledBannerFactory(
            start_date=date,
            end_date=date + timedelta(days=4)
        )

    def test_create_overlapping_banners(self, current_banner, date):
        # Banner overlapping on end
        with pytest.raises(ValidationValueError) as e:
            ScheduledBannerFactory(
                start_date=date + timedelta(days=3),
                end_date=date + timedelta(days=6)
            )
        assert e.value.message == 'Banners dates cannot be overlapping.'

        # Banner overlapping on start
        with pytest.raises(ValidationValueError) as e:
            ScheduledBannerFactory(
                start_date=date - timedelta(days=1),
                end_date=date + timedelta(days=1)
            )
        assert e.value.message == 'Banners dates cannot be overlapping.'

        # Banner overlapping in middle
        with pytest.raises(ValidationValueError) as e:
            ScheduledBannerFactory(
                start_date=date + timedelta(days=1),
                end_date=date + timedelta(days=2)
            )
        assert e.value.message == 'Banners dates cannot be overlapping.'

        # Banner with invalid start/end dates
        with pytest.raises(ValidationValueError) as e:
            ScheduledBannerFactory(
                start_date=date + timedelta(days=8),
                end_date=date + timedelta(days=7)
            )
        assert e.value.message == 'Start date must be before end date.'

        # Banner ends right before next starts
        ScheduledBannerFactory(
            start_date=date - timedelta(days=3),
            end_date=date - timedelta(days=1)
        )

        # Banner begins right after previous ends
        ScheduledBannerFactory(
            start_date=date + timedelta(days=5)
        )
