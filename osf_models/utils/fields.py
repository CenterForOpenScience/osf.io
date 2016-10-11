from django.db import models


class LowercaseCharField(models.CharField):
    def get_prep_value(self, value):
        value = super(models.CharField, self).get_prep_value(value)
        if value is not None:
            value = value.lower()
        return value
