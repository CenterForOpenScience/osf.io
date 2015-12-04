from django.db import models
from django.contrib.auth.models import User

class OsfUser(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="osf_user")
    osf_id = models.CharField(max_length=10)
