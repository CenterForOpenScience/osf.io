from django.db import models

# from osf_models.models.user import User
# from osf_models.models.node import Node


class Contributor(models.Model):
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)

    user = models.ForeignKey('User')
    node = models.ForeignKey('Node')
