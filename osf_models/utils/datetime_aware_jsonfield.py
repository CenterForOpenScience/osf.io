import ujson
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core import exceptions
from psycopg2.extras import Json


class DatetimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=ujson.dumps)
        return value

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=ujson.dumps)
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            ujson.dumps(value)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)
