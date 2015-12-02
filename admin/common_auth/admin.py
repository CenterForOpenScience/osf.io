from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from .models import MyUser

from django.contrib.auth.forms import PasswordResetForm, UserCreationForm

class PermissionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'codename']

class CustomUserRegistrationForm(UserCreationForm):
    class Meta:
            model = MyUser
            fields = ['password', 'first_name', 'last_name', 'email', 'is_active', 'is_staff',
            'is_superuser', 'groups', 'user_permissions', 'last_login', ]
    def __init__(self, *args, **kwargs):
        super(CustomUserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserRegistrationForm
    list_display = ['email', 'first_name', 'last_name', 'is_active']
    fieldsets = (
        (None, {'fields': ('email', 'password',)}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'date_joined', 'last_login',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    add_fieldsets = (
        (None, {'fields':
                ('email', 'first_name', 'last_name', 'password1', 'password2'),
                }),)
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('last_name', 'first_name',)
    actions = ['send_email_invitation']

    def send_email_invitation(self, request, queryset):
        for user in queryset:
            if user.is_active is False:  # email doesn't send unless user is active
                user.is_active = True
                user.save()
            reset_form = PasswordResetForm({'email': user.email}, request.POST)
            assert reset_form.is_valid()
            reset_form.save(
                #subject_template_name='templates/emails/account_creation_subject.txt',
                #email_template_name='templates/emails/invitation_email.html',
                request=request
            )
            user.is_active = False
            user.save()

        self.message_user(request, 'Email invitation sent successfully')
    send_email_invitation.short_description = 'Send email invitation to selected users'

    def save_model(self, request, obj, form, change):
        if change:
            pass
        else:
            obj.is_active = False
        obj.save()

admin.site.register(MyUser, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
