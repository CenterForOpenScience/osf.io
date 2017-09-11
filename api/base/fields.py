from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError


class NullModelMultipleChoiceCaseInsensitiveField(forms.ModelMultipleChoiceField):

    def clean(self, value):
        # let a custom filter handle the actual filtering for null values later in the qs
        if value == 'null':
            return value

        try:
            return super(NullModelMultipleChoiceCaseInsensitiveField, self).clean(value)

        except ValidationError as validation_error:
            # Check to make sure the validation error wasn't because of a case sensitive relationship query
            q = Q()
            for choice in value:
                q |= Q(**{'{}__iexact'.format(self.to_field_name): choice})
            queryset = self.queryset.filter(q)

            if not queryset:
                raise validation_error

            return queryset
