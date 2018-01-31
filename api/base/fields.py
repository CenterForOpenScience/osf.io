from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError


class NullModelMultipleChoiceCaseInsensitiveField(forms.ModelMultipleChoiceField):

    def __init__(self, *args, **kwargs):
        # use the default empty label -- it looks like the latest release did something different here
        # with null values that we'd need to look into that might make this whole thing go away!!!
        kwargs.pop('empty_label')
        super(NullModelMultipleChoiceCaseInsensitiveField, self).__init__(*args, **kwargs)

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
