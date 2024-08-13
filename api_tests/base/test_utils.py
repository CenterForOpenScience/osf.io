from unittest import mock
import unittest
import pytest
from importlib import import_module
from django.conf import settings as django_conf_settings

from rest_framework import fields
from rest_framework.exceptions import ValidationError
from api.base import utils as api_utils

from framework.status import push_status_message

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


class TestTruthyFalsy:
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert api_utils.TRUTHY == fields.BooleanField.TRUE_VALUES

    def test_falsy(self):
        assert api_utils.FALSY == fields.BooleanField.FALSE_VALUES


class TestIsDeprecated(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.min_version = '2.0'
        self.max_version = '2.5'

    def test_is_deprecated(self):
        request_version = '2.6'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is True

    def test_is_not_deprecated(self):
        request_version = '2.5'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is False

    def test_is_deprecated_larger_versions(self):
        request_version = '2.10'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is True


@pytest.mark.django_db
class TestFlaskDjangoIntegration:
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                with mock.patch('framework.status.get_session', return_value=SessionStore()):
                    push_status_message(status_message, kind=status)
            except BaseException:
                assert False, f'Exception from push_status_message via API v2 with type "{status}".'

    def test_push_status_message_expected_error(self):
        status_message = 'This is a message'
        try:
            push_status_message(status_message, kind='error')
            assert False, 'push_status_message() should have generated a ValidationError exception.'

        except ValidationError as e:
            assert (
                e.detail[0] == status_message
            ), 'push_status_message() should have passed along the message with the Exception.'

        except RuntimeError:
            assert False, 'push_status_message() should have caught the runtime error and replaced it.'

        except BaseException:
            assert False, 'Exception from push_status_message when called from the v2 API with type "error"'

    @mock.patch('framework.status.get_session')
    def test_push_status_message_unexpected_error(self, mock_get_session):
        status_message = 'This is a message'
        exception_message = 'this is some very unexpected problem'
        mock_session = mock.Mock()
        mock_session.attach_mock(mock.Mock(side_effect=RuntimeError(exception_message)), 'get')
        mock_get_session.return_value = mock_session
        try:
            push_status_message(status_message, kind='error')
            assert False, 'push_status_message() should have generated a RuntimeError exception.'
        except ValidationError:
            assert False, 'push_status_message() should have re-raised the RuntimeError not gotten ValidationError.'
        except RuntimeError as e:
            assert str(e) == exception_message, (
                'push_status_message() should have re-raised the '
                'original RuntimeError with the original message.'
            )

        except BaseException:
            assert False, (
                'Unexpected Exception from push_status_message when called '
                'from the v2 API with type "error"'
            )
