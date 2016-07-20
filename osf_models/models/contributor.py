from django.db import models


class Contributor(models.Model):
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)

    user = models.ForeignKey('OSFUser')
    node = models.ForeignKey('Node')

    class Meta:
        unique_together = ('user', 'node')
