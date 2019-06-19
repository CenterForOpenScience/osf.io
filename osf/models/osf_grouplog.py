from include import IncludeManager

from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from website.util import api_v2_url


class OSFGroupLog(ObjectIDMixin, BaseModel):
    objects = IncludeManager()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    GROUP_CREATED = 'group_created'

    MEMBER_ADDED = 'member_added'
    MANAGER_ADDED = 'manager_added'
    MEMBER_REMOVED = 'member_removed'
    ROLE_UPDATED = 'role_updated'
    EDITED_NAME = 'edit_name'
    NODE_CONNECTED = 'node_connected'
    NODE_PERMS_UPDATED = 'node_permissions_updated'
    NODE_DISCONNECTED = 'node_disconnected'

    actions = ([GROUP_CREATED, MEMBER_ADDED, MANAGER_ADDED, MEMBER_REMOVED, ROLE_UPDATED,
    EDITED_NAME, NODE_CONNECTED, NODE_PERMS_UPDATED, NODE_DISCONNECTED])

    action_choices = [(action, action.upper()) for action in actions]

    action = models.CharField(max_length=255, db_index=True)
    params = DateTimeAwareJSONField(default=dict)
    should_hide = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', related_name='group_logs', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)
    group = models.ForeignKey('OSFGroup', related_name='logs',
                             db_index=True, null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return ('({self.action!r}, user={self.user!r}, group={self.group!r}, params={self.params!r}) '
                'with id {self.id!r}').format(self=self)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

    @property
    def absolute_api_v2_url(self):
        path = '/logs/{}/'.format(self._id)
        return api_v2_url(path)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_url(self):
        return self.absolute_api_v2_url
