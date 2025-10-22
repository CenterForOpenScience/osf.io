from django.db import models
from django.db.models import ForeignKey, IntegerField

from osf.models import Institution
from osf.models.base import BaseModel


class ProjectLimitNumberDefault(BaseModel):
    institution = ForeignKey(Institution, related_name='project_limit_number_default', on_delete=models.CASCADE)
    project_limit_number = IntegerField()

    class Meta:
        db_table = 'osf_project_limit_number_default'
