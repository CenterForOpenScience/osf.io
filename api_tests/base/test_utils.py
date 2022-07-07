# -*- coding: utf-8 -*-
from nose.tools import *  # noqa:
import pytest
import mock  # noqa

from rest_framework import fields
from rest_framework.exceptions import ValidationError
from api.base import utils as api_utils

from framework.status import push_status_message
from tests.base import OsfTestCase


@pytest.mark.django_db
class TestTruthyFalsy:
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert_equal(api_utils.TRUTHY, fields.BooleanField.TRUE_VALUES)

    def test_falsy(self):
        assert_equal(api_utils.FALSY, fields.BooleanField.FALSE_VALUES)


class TestIsDeprecated(OsfTestCase):

    def setUp(self):
        super(TestIsDeprecated, self).setUp()
        self.min_version = '2.0'
        self.max_version = '2.5'

    def test_is_deprecated(self):
        request_version = '2.6'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version)
        assert_equal(is_deprecated, True)

    def test_is_not_deprecated(self):
        request_version = '2.5'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version)
        assert_equal(is_deprecated, False)

    def test_is_deprecated_larger_versions(self):
        request_version = '2.10'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version
        )
        assert is_deprecated is True


@pytest.mark.django_db
class TestFlaskDjangoIntegration:
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                push_status_message(status_message, kind=status)
            except BaseException:
                assert_true(
                    False,
                    'Exception from push_status_message via API v2 with type "{}".'.format(status)
                )

    def test_push_status_message_expected_error(self):
        status_message = 'This is a message'
        try:
            push_status_message(status_message, kind='error')
            assert_true(
                False,
                'push_status_message() should have generated a ValidationError exception.'
            )
        except ValidationError as e:
            assert_equal(
                e.detail[0],
                status_message,
                'push_status_message() should have passed along the message with the Exception.'
            )
        except RuntimeError:
            assert_true(
                False,
                'push_status_message() should have caught the runtime error and replaced it.'
            )
        except BaseException:
            assert_true(
                False,
                'Exception from push_status_message when called from the v2 API with type "error"'
            )

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
            assert_true(
                False,
                'push_status_message() should have generated a RuntimeError exception.'
            )
        except ValidationError:
            assert_true(
                False,
                'push_status_message() should have re-raised the RuntimeError not gotten ValidationError.'
            )
        except RuntimeError as e:
            assert_equal(str(e),
                         exception_message,
                         'push_status_message() should have re-raised the '
                         'original RuntimeError with the original message.')
        except BaseException:
            assert_true(
                False, 'Unexpected Exception from push_status_message when called '
                'from the v2 API with type "error"')
