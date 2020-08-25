from django.db import models
from include import IncludeManager

from osf.utils.fields import NonNaiveDateTimeField
from osf.utils import permissions


class AbstractBaseContributor(models.Model):
    objects = IncludeManager()

    primary_identifier_name = 'user__guids___id'

    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'visible={self.visible}, '
                'permission={self.permission}'
                ')>').format(self=self)

    class Meta:
        abstract = True

    @property
    def bibliographic(self):
        return self.visible

    @property
    def permission(self):
        return get_contributor_permission(self, self.node)


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


class PreprintContributor(AbstractBaseContributor):
    preprint = models.ForeignKey('Preprint', on_delete=models.CASCADE)

    @property
    def _id(self):
        return '{}-{}'.format(self.preprint._id, self.user._id)

    @property
    def permission(self):
        return get_contributor_permission(self, self.preprint)

    class Meta:
        unique_together = ('user', 'preprint')
        # Make contributors orderable
        # NOTE: Adds an _order column
        order_with_respect_to = 'preprint'


class InstitutionalContributor(AbstractBaseContributor):
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'institution')


class DraftRegistrationContributor(AbstractBaseContributor):
    draft_registration = models.ForeignKey('DraftRegistration', on_delete=models.CASCADE)

    @property
    def permission(self):
        return get_contributor_permission(self, self.draft_registration)

    @property
    def _id(self):
        return '{}-{}'.format(self.draft_registration._id, self.user._id)

    class Meta:
        unique_together = ('user', 'draft_registration')
        order_with_respect_to = 'draft_registration'


class RecentlyAddedContributor(models.Model):
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)  # the user who added the contributor
    contributor = models.ForeignKey('OSFUser', related_name='recently_added_by', on_delete=models.CASCADE)  # the added contributor
    date_added = NonNaiveDateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'contributor')


def get_contributor_permission(contributor, resource):
    """
    Returns a contributor's permissions - perms through contributorship only. No permissions through osf group membership.
    """
    read = resource.format_group(permissions.READ)
    write = resource.format_group(permissions.WRITE)
    admin = resource.format_group(permissions.ADMIN)
    # Checking for django group membership allows you to also get the intended permissions of unregistered contributors
    user_groups = contributor.user.groups.filter(name__in=[read, write, admin]).values_list('name', flat=True)
    if admin in user_groups:
        return permissions.ADMIN
    elif write in user_groups:
        return permissions.WRITE
    elif read in user_groups:
        return permissions.READ
    else:
        return None
