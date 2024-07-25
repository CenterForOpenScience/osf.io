from unittest import mock
import pytz
import pytest
import itsdangerous
from datetime import datetime, timedelta
from importlib import import_module

from django.utils import timezone
from django.conf import settings as django_conf_settings

from website import settings

from osf_tests.factories import (
    AuthUserFactory,
)
from tests.base import OsfTestCase
from tests.utils import run_celery_tasks

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestUserLastLoginDate(OsfTestCase):

    def setUp(self):
        super().setUp()

        self.user = AuthUserFactory()

        self.session = SessionStore()
        self.session['auth_user_id'] = self.user._id
        self.session['auth_user_username'] = self.user.username
        self.session.create()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session.session_key).decode()

    @mock.patch.object(timezone, 'now')
    def test_date_last_login_updated_from_none(self, mock_time):
        now = datetime(2018, 2, 4, tzinfo=pytz.utc)
        mock_time.return_value = now
        assert self.user.date_last_login is None

        self.app.set_cookie(settings.COOKIE_NAME, self.cookie)
        with run_celery_tasks():
            self.app.get(f'{settings.DOMAIN}{self.user._id}')  # user page will fail because not emberized

        self.user.refresh_from_db()
        assert self.user.date_last_login == now

    @mock.patch.object(timezone, 'now')
    def test_date_last_login_updated_below_threshold(self, mock_time):
        now = datetime(2018, 2, 4, tzinfo=pytz.utc)
        mock_time.return_value = now
        self.user.date_last_login = now
        self.user.save()

        # Time is mocked one second below the last login date threshold, so it should not change.
        mock_time.return_value = now + (settings.DATE_LAST_LOGIN_THROTTLE_DELTA - timedelta(seconds=1))
        self.app.set_cookie(settings.COOKIE_NAME, self.cookie)
        with run_celery_tasks():
            self.app.get(f'{settings.DOMAIN}{self.user._id}')  # user page will fail because not emberized

        self.user.refresh_from_db()
        # date_last_login is unchanged
        assert self.user.date_last_login == now

    @mock.patch.object(timezone, 'now')
    def test_date_last_login_updated_above_threshold(self, mock_time):
        now = datetime(2018, 2, 4, tzinfo=pytz.utc)
        mock_time.return_value = now
        self.user.date_last_login = now
        self.user.save()

        # Time is mocked one second below the last login date threshold, so it should not change.
        new_time = now + (settings.DATE_LAST_LOGIN_THROTTLE_DELTA + timedelta(seconds=1))
        mock_time.return_value = new_time
        self.app.set_cookie(settings.COOKIE_NAME, self.cookie)
        with run_celery_tasks():
            self.app.get(f'{settings.DOMAIN}{self.user._id}')  # user page will fail because not emberized

        self.user.refresh_from_db()
        # date_last_login is changed!
        assert self.user.date_last_login == new_time
