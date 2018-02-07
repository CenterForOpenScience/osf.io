from django.db import models
from include import IncludeManager

from osf.utils.fields import NonNaiveDateTimeField
from website.util.permissions import (
    READ,
    WRITE,
    ADMIN,
)


class AbstractBaseContributor(models.Model):
    objects = IncludeManager()

    primary_identifier_name = 'user__guids___id'

    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'read={self.read}, write={self.write}, admin={self.admin}, '
                'visible={self.visible}'
                ')>').format(self=self)

    class Meta:
        abstract = True

    @property
    def bibliographic(self):
        return self.visible

    @property
    def permission(self):
        if self.admin:
            return 'admin'
        if self.write:
            return 'write'
        return 'read'

class Contributor(AbstractBaseContributor):
    node = models.ForeignKey('AbstractNode', on_delete=models.CASCADE)

    @property
    def _id(self):
        return '{}-{}'.format(self.node._id, self.user._id)

    class Meta:
        unique_together = ('user', 'node')
        # Make contributors orderable
        # NOTE: Adds an _order column
        order_with_respect_to = 'node'

class InstitutionalContributor(AbstractBaseContributor):
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'institution')

class RecentlyAddedContributor(models.Model):
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)  # the user who added the contributor
    contributor = models.ForeignKey('OSFUser', related_name='recently_added_by', on_delete=models.CASCADE)  # the added contributor
    date_added = NonNaiveDateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'contributor')

def get_contributor_permissions(contributor, as_list=True):
    perm = []
    if contributor.read:
        perm.append(READ)
    if contributor.write:
        perm.append(WRITE)
    if contributor.admin:
        perm.append(ADMIN)
    if as_list:
        return perm
    else:
        return perm[-1]
