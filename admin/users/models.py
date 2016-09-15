from django.db import models


class TemporaryWorkshopFollowUp(models.Model):
    # Given
    date = models.DateTimeField(default=None)
    name = models.CharField(max_length=100, default=None)
    email = models.EmailField(default=None)

    # Retrieved
    osf_id = models.CharField(max_length=5, default=None)
    log_count = models.IntegerField(default=0)
    node_count = models.IntegerField(default=0)
    last_active = models.DateTimeField(default=None)
