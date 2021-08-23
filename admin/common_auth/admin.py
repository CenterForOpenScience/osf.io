from __future__ import absolute_import

from django.contrib import admin
from django.contrib.admin.models import DELETION
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.html import escape

from osf.models import AdminLogEntry
from osf.models import AdminProfile


class PermissionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'codename']

class AdminAdmin(admin.ModelAdmin):

    def permission_groups(self):
        perm_groups = ', '.join(
            [perm.name for perm in self.user.groups.all()]) if self.user.groups.all() else 'No permission groups'
        return u'<a href="/account/register/?id={id}">{groups}</a>'.format(id=self.user._id, groups=perm_groups)

    def user_name(self):
        return self.user.username

    def _id(self):
        return self.user._id

    permission_groups.allow_tags = True
    permission_groups.short_description = 'Permission Groups'

    list_display = [user_name, _id, permission_groups]


admin.site.register(Permission, PermissionAdmin)
admin.site.register(AdminProfile, AdminAdmin)


class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    readonly_fields = [f.name for f in AdminLogEntry._meta.get_fields()]

    list_filter = [
        'user',
        'action_flag'
    ]

    search_fields = [
        'object_repr',
        'change_message'
    ]

    list_display = [
        'action_time',
        'user',
        'object_link',
        'object_id',
        'message',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        elif obj.content_type is None:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = u'<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'

    def queryset(self, request):
        return super(LogEntryAdmin, self).queryset(request) \
            .prefetch_related('content_type')


# admin.site.register(AdminLogEntry, LogEntryAdmin)
