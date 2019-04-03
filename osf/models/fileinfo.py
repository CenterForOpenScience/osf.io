from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class FileInfo(ObjectIDMixin, BaseModel):
    """Saves extra information about a file."""
    file = models.OneToOneField('osf.BaseFileNode', on_delete=models.CASCADE)
    file_size = models.IntegerField()
