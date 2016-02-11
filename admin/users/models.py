from django.db import models


class OSFUser(models.Model):
    osf_id = models.CharField(max_length=5)
    notes = models.TextField(verbose_name='Notes for OSF user')
