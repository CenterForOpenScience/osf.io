from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class TimestampTask(ObjectIDMixin, BaseModel):
    """Saves celery's task id for a project."""
    node = models.OneToOneField('Node', on_delete=models.CASCADE)
    task_id = models.CharField(max_length=80)
    requester = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
