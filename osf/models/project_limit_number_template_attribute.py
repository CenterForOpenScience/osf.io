from django.db import models

from admin.base import settings
from osf.models.base import BaseModel
from osf.models.project_limit_number_template import ProjectLimitNumberTemplate


class ProjectLimitNumberTemplateAttribute(BaseModel):
    template = models.ForeignKey(ProjectLimitNumberTemplate, related_name='attributes', on_delete=models.CASCADE)
    attribute_name = models.CharField(max_length=255)
    setting_type = models.IntegerField(choices=settings.SETTING_TYPE)
    attribute_value = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'osf_project_limit_number_template_attribute'
