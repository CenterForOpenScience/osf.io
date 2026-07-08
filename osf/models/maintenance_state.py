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


class MaintenanceMode(models.Model):
    maintenance_mode = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def is_under_maintenance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj.maintenance_mode
