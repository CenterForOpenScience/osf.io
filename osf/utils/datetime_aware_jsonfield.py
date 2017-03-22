from __future__ import unicode_literals

import datetime as dt
import json
import logging
from decimal import Decimal
from functools import partial

import pytz
import ciso8601
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.forms.jsonb import JSONField as JSONFormField
from django.core.serializers.json import DjangoJSONEncoder
from osf.exceptions import NaiveDatetimeException, ValidationError
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

def coerce_nonnaive_datetimes(json_data):
    if isinstance(json_data, list):
        coerced_data = [coerce_nonnaive_datetimes(data) for data in json_data]
    elif isinstance(json_data, dict):
        coerced_data = dict()
        for key, value in json_data.iteritems():
            coerced_data[key] = coerce_nonnaive_datetimes(value)
    elif isinstance(json_data, dt.datetime):
        try:
            worked = json_data.astimezone(pytz.utc)  # aware object can be in any timezone # noqa
        except ValueError:  # naive
            coerced_data = json_data.replace(tzinfo=pytz.utc)  # json_data must be in UTC
        else:
            coerced_data = json_data  # it's already aware
    else:
        coerced_data = json_data

    return coerced_data


class DateTimeAwareJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, dt.datetime):
            if o.tzinfo is None or o.tzinfo.utcoffset(o) is None:
                raise NaiveDatetimeException('Tried to encode a naive datetime.')
            return dict(type='encoded_datetime', value=o.isoformat())
        elif isinstance(o, dt.date):
            return dict(type='encoded_date', value=o.isoformat())
        elif isinstance(o, dt.time):
            if o.tzinfo is None or o.tzinfo.utcoffset(o) is None:
                raise NaiveDatetimeException('Tried to encode a naive time.')
            return dict(type='encoded_time', value=o.isoformat())
        elif isinstance(o, Decimal):
            return dict(type='encoded_decimal', value=str(o))
        return super(DateTimeAwareJSONEncoder, self).default(o)


def decode_datetime_objects(nested_value):
    if isinstance(nested_value, list):
        return [decode_datetime_objects(item) for item in nested_value]
    elif isinstance(nested_value, dict):
        for key, value in nested_value.iteritems():
            if isinstance(value, dict) and 'type' in value.keys():
                if value['type'] == 'encoded_datetime':
                    nested_value[key] = ciso8601.parse_datetime(value['value'])
                if value['type'] == 'encoded_date':
                    nested_value[key] = ciso8601.parse_datetime(value['value']).date()
                if value['type'] == 'encoded_time':
                    nested_value[key] = ciso8601.parse_datetime(value['value']).time()
                if value['type'] == 'encoded_decimal':
                    nested_value[key] = Decimal(value['value'])
            elif isinstance(value, dict):
                nested_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                nested_value[key] = decode_datetime_objects(value)
        return nested_value
    return nested_value


class DateTimeAwareJSONField(JSONField):
    def formfield(self, **kwargs):
        defaults = {'form_class': DateTimeAwareJSONFormField}
        defaults.update(kwargs)
        return super(DateTimeAwareJSONField, self).formfield(**defaults)

    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return value

    def from_db_value(self, value, expression, connection, context):
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

class DateTimeAwareJSONFormField(JSONFormField):
    def to_python(self, value):
        try:
            return decode_datetime_objects(json.loads(value))
        except TypeError:
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def prepare_value(self, value):
        try:
            return json.dumps(value, cls=DateTimeAwareJSONEncoder)
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
