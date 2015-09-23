"""
Tests related to functions in framework.mongo
"""
from unittest import TestCase

from nose.tools import *  # flake8: noqa

from modularodm.exceptions import ValidationValueError

from framework.mongo import validators

class TestValidators(TestCase):
    def test_string_required_passes_with_string(self):
        assert_true(validators.string_required('Hi!'))

    def test_string_required_fails_when_empty(self):

        with assert_raises(ValidationValueError):
            validators.string_required(None)
            validators.string_required('')

    def test_choice_validator_finds_only_exact_match(self):
        new_validator = validators.choice_in(('value1', 'value2', 'VaLuE3', 123),
                                             ignore_case=False)

        assert_true(new_validator('value1'))
        assert_true(new_validator('VaLuE3'))
        assert_true(new_validator(123))

        with assert_raises(ValidationValueError):
            new_validator('VALue2')

    def choice_validator_fails_when_option_not_present(self):
        new_validator = validators.choice_in(('value1', 'value2', 'VaLuE3', 123),
                                             ignore_case=False)
        with assert_raises(ValidationValueError):
            new_validator('You')
            new_validator('123')
            new_validator(456)

    def choice_validator_case_insensitive(self):
        new_validator = validators.choice_in(('value1', 'value2', 'VaLuE3', 123),
                                             ignore_case=True)
        assert_true(new_validator('VaLuE3'))
        assert_true(new_validator('value3'))
        assert_true(new_validator(123))

        with assert_raises(ValidationValueError):
            new_validator('123')
