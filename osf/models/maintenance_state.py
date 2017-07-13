from django.db import models

from osf.utils.fields import NonNaiveDateTimeField

LEVELS = [
    (1, 'info'),
    (2, 'warning'),
    (3, 'danger'),
]

class MaintenanceState(models.Model):

    _id = models.CharField(unique=True, max_length=255, help_text="An identifier for this maintenance state, i.e. 'rackspace', 'maintenance'")
    level = models.IntegerField(choices=LEVELS, default=1)
    start = NonNaiveDateTimeField()
    end = NonNaiveDateTimeField()
    message = models.TextField()
