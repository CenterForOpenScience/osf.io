from django.db import models
from django.db.models import ForeignKey

from osf.models import Institution
from osf.models.base import BaseModel
from osf.models.project_limit_number_template import ProjectLimitNumberTemplate


class ProjectLimitNumberSetting(BaseModel):
    institution = ForeignKey(Institution, related_name='project_limit_number_settings', on_delete=models.CASCADE)
    template = ForeignKey(ProjectLimitNumberTemplate, related_name='settings', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    project_limit_number = models.IntegerField()
    priority = models.IntegerField()
    memo = models.CharField(max_length=255, null=True, blank=True)
    is_availability = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'osf_project_limit_number_setting'
