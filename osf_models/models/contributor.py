from django.db import models


class AbstractBaseContributor(models.Model):
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser')

    class Meta:
        abstract = True

class Contributor(AbstractBaseContributor):
    node = models.ForeignKey('AbstractNode')

    class Meta:
        unique_together = ('user', 'node')

class InstitutionalContributor(AbstractBaseContributor):
    institution = models.ForeignKey('Institution')

    class Meta:
        unique_together = ('user', 'institution')
