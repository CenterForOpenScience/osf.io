# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from rest_framework import fields

from api.base import utils as api_utils

from tests.base import ApiTestCase


class TruthyFalsyTestCase(ApiTestCase):
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert_equal(api_utils.TRUTHY, fields.BooleanField.TRUE_VALUES)

    def test_falsy(self):
        assert_equal(api_utils.FALSY, fields.BooleanField.FALSE_VALUES)
