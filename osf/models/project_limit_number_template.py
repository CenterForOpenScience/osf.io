from django.db import models

from osf.models.base import BaseModel


class ProjectLimitNumberTemplate(BaseModel):
    template_name = models.CharField(max_length=255)
    is_availability = models.BooleanField(default=True)
    used_setting_number = models.IntegerField(default=0, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'osf_project_limit_number_template'
