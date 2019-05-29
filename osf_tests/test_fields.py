import datetime as dt
import json
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from osf.models import BaseFileNode
from osf_tests.factories import ProjectFactory
from tests.test_websitefiles import TestFileNode

from osf.utils.datetime_aware_jsonfield import (DateTimeAwareJSONEncoder,
                                                decode_datetime_objects)


class DateTimeAwareJSONFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.json_dict_data = dict(
            sample_date=dt.date.today(),
            nested_data=dict(
                sample_date=dt.date.today(),
                sample_datetime=timezone.now(),
                sample_decimal=Decimal('10.259')
            ),
            sample_datetime=timezone.now(),
            sample_decimal=Decimal('10.259'),
            sample_text='wut wut',
            list_of_things=[
                dict(
                    sample_date=dt.date.today(),
                    sample_datetime=timezone.now(),
                    sample_decimal=Decimal('10.259')
                ),
                dict(
                    sample_date=dt.date.today(),
                    sample_datetime=timezone.now(),
                    sample_decimal=Decimal('10.259')
                ),
                [
                    dict(
                        sample_date=dt.date.today(),
                        sample_datetime=timezone.now(),
                        sample_decimal=Decimal('10.259')
                    ),
                    dict(
                        sample_date=dt.date.today(),
                        sample_datetime=timezone.now(),
                        sample_decimal=Decimal('10.259')
                    ),
                ]
            ]
        )
        cls.json_list_data = [
            dict(
                sample_date=dt.date.today(),
                sample_datetime=timezone.now(),
                sample_decimal=Decimal('10.259')
            ),
            dict(
                sample_date=dt.date.today(),
                sample_datetime=timezone.now(),
                sample_decimal=Decimal('10.259')
            ),
        ]

    def test_dict(self):
        json_string = json.dumps(self.json_dict_data, cls=DateTimeAwareJSONEncoder)
        json_data = decode_datetime_objects(json.loads(json_string))
        assert json_data == self.json_dict_data, 'Nope'

    def test_list(self):
        json_string = json.dumps(self.json_list_data, cls=DateTimeAwareJSONEncoder)
        json_data = decode_datetime_objects(json.loads(json_string))
        assert json_data == self.json_list_data, 'Nope'

    def test_list_field(self):
        field = TestFileNode.objects.create(history=self.json_list_data, target=self.project)
        iden = field.id
        assert BaseFileNode.objects.get(id=iden).history == self.json_list_data

    def test_dict_field(self):
        d = TestFileNode.objects.create(history=self.json_dict_data, target=self.project)
        iden = d.id
        assert BaseFileNode.objects.get(id=iden).history == self.json_dict_data
