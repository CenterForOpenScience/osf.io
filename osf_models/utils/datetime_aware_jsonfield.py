import datetime as dt
import json
from decimal import Decimal
from functools import partial

from dateutil import parser
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from osf_models.exceptions import ValidationError
from psycopg2.extras import Json


class DateTimeAwareJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, dt.datetime):
            return dict(type='encoded_datetime', value=o.isoformat())
        elif isinstance(o, dt.date):
            return dict(type='encoded_date', value=o.isoformat())
        elif isinstance(o, dt.time):
            return dict(type='encoded_time', value=o.isoformat())
        elif isinstance(o, Decimal):
            return dict(type='encoded_decimal', value=str(o))
        return super(DateTimeAwareJSONEncoder, self).default(o)


def decode_datetime_objects(nested_value):

    if isinstance(nested_value, list):
        new_list = list()
        for item in nested_value:
            new_list.append(decode_datetime_objects(item))
        return new_list
    elif isinstance(nested_value, dict):
        new_value = nested_value
        for key, value in nested_value.iteritems():
            if isinstance(value, dict) and 'type' in value.keys():
                if value['type'] == 'encoded_datetime':
                    new_value[key] = parser.parse(value['value'])
                if value['type'] == 'encoded_date':
                    new_value[key] = parser.parse(value['value']).date()
                if value['type'] == 'encoded_time':
                    new_value[key] = parser.parse(value['value']).time()
                if value['type'] == 'encoded_decimal':
                    new_value[key] = Decimal(value['value'])
            elif isinstance(value, dict):
                new_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                new_value[key] = decode_datetime_objects(value)
        return new_value
    return nested_value



# def decode_datetime_objects(nested_value):
#     if isinstance(nested_value, dict):
#         new_value = dict()
#         for key, value in nested_value.iteritems():
#             if key == 'type' and value == 'encoded_datetime':
#                 new_value[key] = parser.parse(nested_value['value'])
#             elif key == 'type' and value == 'encoded_date':
#                 new_value[key] = parser.parse(nested_value['value'])
#             elif key == 'type' and value == 'encoded_time':
#                 new_value[key] = parser.parse(nested_value['value'])
#             elif isinstance(value, collections.Mapping):
#                 # recurse
#                 new_value[key] = decode_datetime_objects(value)
#         return new_value
#     elif isinstance(nested_value, list):
#         new_list = list()
#         for item in nested_value:
#             # recurse
#             new_value = decode_datetime_objects(item)
#             new_list.append(new_value)
#         return new_list
#     return nested_value


class DateTimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return value

    def to_python(self, value):
        if value is None:
            return None
        return super(DateTimeAwareJSONField, self).to_python(decode_datetime_objects(value))


    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            json.dumps(value, cls=DateTimeAwareJSONEncoder)
        except TypeError:
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)
