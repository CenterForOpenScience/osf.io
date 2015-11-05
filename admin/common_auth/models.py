from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class AdminUser(models.Model):
	user = models.OneToOneField(User)

	def __unicode__(self):
		return self.user.username
