import re
from rest_framework import serializers as ser
from django.core.exceptions import ValidationError


class DOIField(ser.CharField):
    def to_internal_value(self, data):
        DOI_REGEX = re.compile(r'^10\.\d+\/[-._;()/:A-Z0-9]+$', re.IGNORECASE)

        if data is None:
            return None
        # Strip known DOI prefixes and domains
        cleaned = re.sub(r'^(?:https?://)?(?:dx\.)?(?:test\.)?(?:doi\.org/)?', '', data, flags=re.IGNORECASE)

        if not DOI_REGEX.match(cleaned):
            raise ValidationError('Invalid DOI format. Must be a valid DOI or DOI URL.')
        return cleaned
