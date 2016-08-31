from django.db import models


class AbstractBaseContributor(models.Model):
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser')

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'read={self.read}, write={self.write}, admin={self.admin}, '
                'visible={self.visible}'
                ')>').format(self=self)

    class Meta:
        abstract = True

class Contributor(AbstractBaseContributor):
    node = models.ForeignKey('AbstractNode')

    class Meta:
        unique_together = ('user', 'node')
        # Make contributors orderable
        # NOTE: Adds an _order column
        order_with_respect_to = 'node'

class InstitutionalContributor(AbstractBaseContributor):
    institution = models.ForeignKey('Institution')

    class Meta:
        unique_together = ('user', 'institution')

class RecentlyAddedContributor(models.Model):
    user = models.ForeignKey('OSFUser')  # the user who added the contributor
    contributor = models.ForeignKey('OSFUser', related_name='recently_added_by')  # the added contributor
    date_added = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'contributor')
