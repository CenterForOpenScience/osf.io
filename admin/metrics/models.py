from django.db import models


class OSFStatistic(models.Model):
    users = models.IntegerField(verbose_name='OSF users')
    date = models.DateTimeField(default=None)
