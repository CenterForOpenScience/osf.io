"""
Tests related to functions in framework.mongo
"""
from unittest import TestCase

from nose.tools import *  # flake8: noqa

from modularodm.exceptions import ValidationError, ValidationValueError

from framework.mongo import validators

class TestValidators(TestCase):

    def test_string_required_passes_with_string(self):
        assert_true(validators.string_required('Hi!'))

    def test_string_required_fails_when_empty(self):

        with assert_raises(ValidationValueError):
            validators.string_required(None)
            validators.string_required('')
