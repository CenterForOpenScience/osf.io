import datetime as dt
import importlib
import os
from unittest import mock

import pytest

from website import settings


class TestLatestTermsOfServiceUpdate:

    def test_defaults_to_the_gdpr_terms_update(self):
        assert settings.LATEST_TERMS_OF_SERVICE_UPDATE == dt.datetime(2018, 5, 25, tzinfo=dt.timezone.utc)

    def test_iso_date_from_environment_is_parsed_and_read_as_utc(self):
        with mock.patch.dict(os.environ, {'LATEST_TERMS_OF_SERVICE_UPDATE': '2026-10-01'}):
            importlib.reload(settings)
            assert settings.LATEST_TERMS_OF_SERVICE_UPDATE == dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)

    def test_iso_datetime_with_offset_from_environment_is_parsed(self):
        with mock.patch.dict(os.environ, {'LATEST_TERMS_OF_SERVICE_UPDATE': '2026-10-01T12:30:00+00:00'}):
            importlib.reload(settings)
            assert settings.LATEST_TERMS_OF_SERVICE_UPDATE == dt.datetime(2026, 10, 1, 12, 30, tzinfo=dt.timezone.utc)