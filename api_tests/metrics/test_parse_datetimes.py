import pytest
import mock

from datetime import datetime
from django.utils import timezone

from rest_framework.exceptions import ValidationError
from api.metrics.utils import parse_datetimes


class TestParseDatetimes:

    @pytest.fixture()
    def start_date(self):
        return '2018-01-01'

    @pytest.fixture()
    def end_date(self):
        return '2019-01-01'

    @mock.patch('api.metrics.utils.timezone.now')
    def test_on_date_and_start_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'on_date': end_date, 'start_datetime': start_date})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_on_date_and_end_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'on_date': start_date, 'end_datetime': end_date})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_end_date_before_start_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'start_datetime': end_date, 'end_datetime': start_date})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_end_date_before_start_on_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'on_date': end_date, 'end_datetime': start_date})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_time_used_for_specifc_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'on_date': '{}T01:01:01'.format(start_date)})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_end_date_but_no_start_date_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({'end_datetime': end_date})
            assert False
        except ValidationError:
            assert True

    @mock.patch('api.metrics.utils.timezone.now')
    def test_time_in_one_but_not_the_other_fails(self, mock_timezone, start_date, end_date):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        try:
            parse_datetimes({
                'end_datetime': end_date,
                'start_datetime': '{}T01:01:01'.format(start_date),
            })
            assert False
        except ValidationError:
            assert True
