from django.db import models

from osf.models import ProjectLimitNumberSetting
from osf.models.base import BaseModel
from osf.models.project_limit_number_template_attribute import ProjectLimitNumberTemplateAttribute


class ProjectLimitNumberSettingAttribute(BaseModel):
    setting = models.ForeignKey(ProjectLimitNumberSetting, related_name='attributes', on_delete=models.CASCADE)
    attribute = models.ForeignKey(ProjectLimitNumberTemplateAttribute, related_name='setting_attributes', on_delete=models.CASCADE)
    attribute_value = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'osf_project_limit_number_setting_attribute'
