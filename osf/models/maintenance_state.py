from django.db import models

from osf.utils.fields import NonNaiveDateTimeField


class MaintenanceState(models.Model):
    start = NonNaiveDateTimeField()
    end = NonNaiveDateTimeField()
