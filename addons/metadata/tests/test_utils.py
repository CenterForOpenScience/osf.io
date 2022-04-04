# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
from tests.base import OsfTestCase

from ..models import RegistrationReportFormat
from ..utils import make_report_as_csv


class TestMakeReportAsCsv(OsfTestCase):

    def test_simple(self):
        format = RegistrationReportFormat.objects.create(
            csv_template='{{example}}',
        )
        data = {
            'example': {
                'value': 'TEST',
            }
        }
        filename, result = make_report_as_csv(format, data)
        assert_equal(filename, 'report.csv')
        assert_equal(result, 'TEST')

    def test_complex_name(self):
        format = RegistrationReportFormat.objects.create(
            csv_template='{{example_data}}',
        )
        data = {
            'example-data': {
                'value': 'TEST',
            }
        }
        filename, result = make_report_as_csv(format, data)
        assert_equal(filename, 'report.csv')
        assert_equal(result, 'TEST')

    def test_quoted(self):
        format = RegistrationReportFormat.objects.create(
            csv_template='{{example_data | quotecsv}}',
        )
        data = {
            'example-data': {
                'value': 'TEST,DATA',
            }
        }
        filename, result = make_report_as_csv(format, data)
        assert_equal(filename, 'report.csv')
        assert_equal(result, '"TEST,DATA"')
