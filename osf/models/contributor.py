from django.db import models
from include import IncludeManager

from osf.utils.fields import NonNaiveDateTimeField


class AbstractBaseContributor(models.Model):
    objects = IncludeManager()

    primary_identifier_name = 'user__guids___id'

    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'visible={self.visible}, '
                'permission={self.permission}, '
                ')>').format(self=self)

    class Meta:
        abstract = True

    @property
    def bibliographic(self):
        return self.visible

    @property
    def permission(self):
        # Checking group membership instead of permissions since unregistered
        # contributors technically have no permissions
        node_id = self.node.id
        user = self.user
        read = 'node_{}_read'.format(node_id)
        write = 'node_{}_write'.format(node_id)
        admin = 'node_{}_admin'.format(node_id)
        user_groups = user.groups.filter(name__in=[read, write, admin]).values_list('name', flat=True)
        if admin in user_groups:
            return 'admin'
        elif write in user_groups:
            return 'write'
        elif read in user_groups:
            return 'read'
        else:
            return None


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


class PreprintContributor(models.Model):
    objects = IncludeManager()

    primary_identifier_name = 'user__guids___id'
    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    preprint = models.ForeignKey('Preprint', on_delete=models.CASCADE)

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'visible={self.visible}, '
                'permission={self.permission}, '
                ')>').format(self=self)

    @property
    def _id(self):
        return '{}-{}'.format(self.preprint._id, self.user._id)

    @property
    def bibliographic(self):
        return self.visible

    @property
    def permission(self):
        # Checking group membership instead of permissions since unregistered
        # contributors technically have no permissions
        preprint_id = self.preprint.id
        user = self.user
        read = 'preprint_{}_read'.format(preprint_id)
        write = 'preprint_{}_write'.format(preprint_id)
        admin = 'preprint_{}_admin'.format(preprint_id)
        user_groups = user.groups.filter(name__in=[read, write, admin]).values_list('name', flat=True)
        if admin in user_groups:
            return 'admin'
        elif write in user_groups:
            return 'write'
        elif read in user_groups:
            return 'read'
        else:
            return None

    class Meta:
        unique_together = ('user', 'preprint')
        # Make contributors orderable
        # NOTE: Adds an _order column
        order_with_respect_to = 'preprint'


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
    node = contributor.node
    user = contributor.user
    perm = []
    if node.has_permission(user, 'read'):
        perm.append('read')
    if node.has_permission(user, 'write'):
        perm.append('write')
    if node.has_permission(user, 'admin'):
        perm.append('admin')
    if as_list:
        return perm
    else:
        return perm[-1]
