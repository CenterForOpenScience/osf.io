from django.db import models


class OSFWebsiteStatistics(models.Model):
    users = models.IntegerField(verbose_name='OSF users', default=0)
    delta_users = models.IntegerField(default=0)
    unregistered_users = models.IntegerField(verbose_name='Unregistered users',
                                             default=0)
    projects = models.IntegerField(verbose_name='Number of projects',
                                   default=0)
    delta_projects = models.IntegerField(default=0)
    public_projects = models.IntegerField(
        verbose_name='Number of public projects', default=0)
    delta_public_projects = models.IntegerField(default=0)
    registered_projects = models.IntegerField(
        verbose_name='Number of projects registered', default=0
    )
    delta_registered_projects = models.IntegerField(default=0)
    date = models.DateTimeField(default=None)
