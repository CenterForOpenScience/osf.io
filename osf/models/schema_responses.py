from django.utils import timezone
from osf.utils.fields import NonNaiveDateTimeField
from django.db import models

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.models.base import GuidMixin, BaseModel


class SchemaResponses(GuidMixin, BaseModel):
    """
    TODO
    - make public behavior
    - moderations behavior
    - check spam when making public behavior
    - delete/discard behavior
    - metadata/DOI behavior
    - email stuff
    """
    _responses = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    public = NonNaiveDateTimeField(null=True, blank=True)
    schema = models.ForeignKey(
        'RegistrationSchema',
        related_name='schema_responses',
        on_delete=models.CASCADE,
    )
    registration = models.ForeignKey(
        'AbstractNode',
        related_name='schema_responses',
        on_delete=models.CASCADE,
    )

    @property
    def responses(self):
        return self._responses

    @responses.setter
    def responses(self, data):
        self.schema.validate_metadata(data)
        self._responses = data

    @property
    def is_public(self):
        return bool(self.public)

    @is_public.setter
    def is_public(self, value):
        if value is True:
            self.public = timezone.now()
        else:
            self.public = None

        self.save()

    def delete(self, *args, **kwargs):
        self.deleted = timezone.now()

        if kwargs.get('save'):
            self.save()

    @property
    def versions(self):
        schema_response = SchemaResponses.objects.get(guids___id=self._id)
        return SchemaResponses.objects.filter(
            deleted__isnull=True,
            public__isnull=False,
            node=schema_response.node,
            schema=schema_response.schema
        )

