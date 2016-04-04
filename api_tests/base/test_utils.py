# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from rest_framework import fields
from rest_framework.exceptions import ValidationError
from api.base import utils as api_utils

from tests.base import ApiTestCase
from framework.status import push_status_message


class TruthyFalsyTestCase(ApiTestCase):
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert_equal(api_utils.TRUTHY, fields.BooleanField.TRUE_VALUES)

    def test_falsy(self):
        assert_equal(api_utils.FALSY, fields.BooleanField.FALSE_VALUES)


class FlaskDjangoIntegrationTestCase(ApiTestCase):
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                push_status_message(status_message, kind=status)
            except:
                assert_true(False, 'Exception from push_status_message via API v2 with type "{}".'.format(status))

    def test_push_status_message_error(self):
        status_message = 'This is a message'
        try:
            push_status_message(status_message, kind='error')
            assert_true(False, 'push_status_message() should have generated a ValidationError exception.')
        except ValidationError as e:
            assert_equal(e.detail[0], status_message,
                         'push_status_message() should have passed along the message with the Exception.')
        except RuntimeError:
            assert_true(False, 'push_status_message() should have caught the runtime error and replaced it.')
        except:
            assert_true(False, 'Exception from push_status_message when called from the v2 API with type "error"')
