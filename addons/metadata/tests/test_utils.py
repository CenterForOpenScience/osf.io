# -*- coding: utf-8 -*-
"""Reporting test for metadata addon"""
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
        schema = {'pages': []}
        filename, result = make_report_as_csv(format, data, schema)
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
        schema = {'pages': []}
        filename, result = make_report_as_csv(format, data, schema)
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
        schema = {'pages': []}
        filename, result = make_report_as_csv(format, data, schema)
        assert_equal(filename, 'report.csv')
        assert_equal(result, '"TEST,DATA"')

    def test_choose_tooltip(self):
        format = RegistrationReportFormat.objects.create(
            csv_template='{{example}},{{example_tooltip}},{{example_tooltip_0}},{{example_tooltip_1}},{{example_tooltip_2}},{{example_tooltip_3}}',
        )
        data = {
            'example': {
                'value': '2',
            }
        }
        schema = {'pages': [
            {
                'questions': [
                    {
                        'qid': 'example',
                        'type': 'choose',
                        'options': [
                            {
                                'text': '1',
                                'tooltip': '一|one',
                            },
                            {
                                'text': '2',
                                'tooltip': '二|two',
                            },
                            {
                                'text': '3',
                                'tooltip': '三|three',
                            },
                        ],
                    }
                ],
            }
        ]}
        filename, result = make_report_as_csv(format, data, schema)
        assert_equal(filename, 'report.csv')
        assert_equal(result, '2,二|two,二,two,,')
