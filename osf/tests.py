import datetime as dt
import json
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONEncoder, decode_datetime_objects


class DateTimeAwareJSONFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
