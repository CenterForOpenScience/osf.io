import datetime as dt
import json
import logging
from decimal import Decimal

import pytz
from dateutil.parser import isoparse
from django.contrib.postgres import lookups
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import JSONField
from django.forms import JSONField as JSONFormField

from osf.exceptions import NaiveDatetimeException, ValidationError

logger = logging.getLogger(__name__)


def coerce_nonnaive_datetimes(json_data):
    if isinstance(json_data, list):
        coerced_data = [coerce_nonnaive_datetimes(data) for data in json_data]
    elif isinstance(json_data, dict):
        coerced_data = dict()
        for key, value in json_data.items():
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
        return super().default(o)


def decode_datetime_objects(nested_value):
    if isinstance(nested_value, list):
        return [decode_datetime_objects(item) for item in nested_value]
    elif isinstance(nested_value, dict):
        for key, value in nested_value.items():
            if isinstance(value, dict) and 'type' in value.keys():
                if value['type'] == 'encoded_datetime':
                    nested_value[key] = isoparse(value['value'])
                if value['type'] == 'encoded_date':
                    nested_value[key] = isoparse(value['value']).date()
                if value['type'] == 'encoded_time':
                    nested_value[key] = isoparse(value['value']).time()
                if value['type'] == 'encoded_decimal':
                    nested_value[key] = Decimal(value['value'])
            elif isinstance(value, dict):
                nested_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                nested_value[key] = decode_datetime_objects(value)
        return nested_value
    return nested_value


class DateTimeAwareJSONField(JSONField):

    def __init__(self, verbose_name=None, name=None, encoder=DateTimeAwareJSONEncoder, **kwargs):
        super().__init__(verbose_name, name, encoder, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': DateTimeAwareJSONFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, None, None)
        return decode_datetime_objects(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        return super(JSONField, self).get_prep_lookup(lookup_type, value)


class DateTimeAwareJSONFormField(JSONFormField):

    def to_python(self, value):
        value = super().to_python(value)
        try:
            return decode_datetime_objects(value)
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
