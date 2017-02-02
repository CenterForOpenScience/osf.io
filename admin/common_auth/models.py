from django.db import models


class AdminProfile(models.Model):

    user = models.OneToOneField('osf.OSFUser', related_name='admin_profile')

    desk_token = models.CharField(max_length=45, blank=True)
    desk_token_secret = models.CharField(max_length=45, blank=True)
