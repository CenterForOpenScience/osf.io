from django.db import models

from osf.utils.fields import NonNaiveDateTimeField

LEVELS = [
    (1, 'info'),
    (2, 'warning'),
    (3, 'danger'),
]

class MaintenanceState(models.Model):

    level = models.IntegerField(choices=LEVELS, default=1)
    start = NonNaiveDateTimeField()
    end = NonNaiveDateTimeField()
    message = models.TextField(blank=True)
