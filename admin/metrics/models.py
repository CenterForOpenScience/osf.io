from django.db import models

from datetime import datetime


class OSFStatistic(models.Model):
    users = models.IntegerField(verbose_name='OSF users')
    date = models.DateTimeField(default=datetime.utcnow())
