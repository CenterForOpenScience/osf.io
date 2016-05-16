from __future__ import absolute_import

from django.contrib import admin
from django.contrib.admin.models import DELETION
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.utils.html import escape

from admin.common_auth.logs import OSFLogEntry
from admin.common_auth.forms import UserRegistrationForm
from admin.common_auth.models import MyUser


class PermissionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'codename']


class CustomUserAdmin(UserAdmin):
    add_form = UserRegistrationForm
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'confirmed', 'osf_id']
    fieldsets = (
        (None, {'fields': ('email', 'password',)}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'date_joined', 'last_login', 'osf_id', 'desk_email', 'desk_password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    add_fieldsets = (
        (None, {'fields':
                ('email', 'first_name', 'last_name', 'password1', 'password2', 'osf_id'),
                }),)
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('last_name', 'first_name',)
    actions = ['send_email_invitation']
    readonly_fields = ('date_joined',)


admin.site.register(MyUser, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)


class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    readonly_fields = [f.name for f in OSFLogEntry._meta.get_fields()]

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


admin.site.register(OSFLogEntry, LogEntryAdmin)
