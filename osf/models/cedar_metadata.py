from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class CedarMetadataTemplate(ObjectIDMixin, BaseModel):
    schema_name = models.CharField(max_length=255, default=None)
    cedar_id = models.CharField(max_length=255, default=None)
    template = DateTimeAwareJSONField(default=dict)
    active = models.BooleanField(default=True)
    template_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ('cedar_id', 'template_version')

    def __unicode__(self):
        return f'(name=[{self.schema_name}], version=[{self.template_version}], id=[{self.cedar_id}])'
