# -*- coding: utf-8 -*-
import mock
import pytest

from api.base import utils as api_utils
from framework.status import push_status_message
from rest_framework import fields
from rest_framework.exceptions import ValidationError


class TestTruthyFalsy:
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert api_utils.TRUTHY == fields.BooleanField.TRUE_VALUES

    def test_falsy(self):
        assert api_utils.FALSY == fields.BooleanField.FALSE_VALUES


class TestIsDeprecated:

    def test_test_is_deprecated(self):

        min_version = '2.0'
        max_version = '2.5'

        #test_is_deprecated
        request_version = '2.6'
        is_deprecated = api_utils.is_deprecated(request_version, min_version, max_version)
        assert is_deprecated is True

        #test_is_not_deprecated
        request_version = '2.5'
        is_deprecated = api_utils.is_deprecated(request_version, min_version, max_version)
        assert is_deprecated is False


class TestFlaskDjangoIntegration:
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                push_status_message(status_message, kind=status)
            except:
                assert False, 'Exception from push_status_message via API v2 with type "{}".'.format(status)

    def test_push_status_message_expected_error(self):
        status_message = 'This is a message'
        try:
            push_status_message(status_message, kind='error')
            assert False, 'push_status_message() should have generated a ValidationError exception.'
        except ValidationError as e:
            assert e.detail[0] == status_message, 'push_status_message() should have passed along the message with the Exception.'
        except RuntimeError:
            assert False, 'push_status_message() should have caught the runtime error and replaced it.'
        except:
            assert False, 'Exception from push_status_message when called from the v2 API with type "error"'

    @mock.patch('framework.status.session')
    def test_push_status_message_unexpected_error(self, mock_sesh):
        status_message = 'This is a message'
        exception_message = 'this is some very unexpected problem'
        mock_get = mock.Mock(side_effect=RuntimeError(exception_message))
        mock_data = mock.Mock()
        mock_data.attach_mock(mock_get, 'get')
        mock_sesh.attach_mock(mock_data, 'data')
        try:
            push_status_message(status_message, kind='error')
            assert False, 'push_status_message() should have generated a RuntimeError exception.'
        except ValidationError as e:
            assert False, 'push_status_message() should have re-raised the RuntimeError not gotten ValidationError.'
        except RuntimeError as e:
            assert (getattr(e, 'message', None) == exception_message), 'push_status_message() should have re-raised the original RuntimeError with the original message.'
        except:
            assert False, 'Unexpected Exception from push_status_message when called from the v2 API with type "error"'
