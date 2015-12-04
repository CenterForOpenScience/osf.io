from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm

class PermissionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'codename']

class CustomUserRegistrationForm(UserCreationForm):

    class Meta:
        model = User
        fields = '__all__'
    def __init__(self, *args, **kwargs):
            super(CustomUserRegistrationForm, self).__init__(*args, **kwargs)
            self.fields['email'].required = True

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active']
    list_filter = ['groups', 'is_staff', 'is_superuser', 'is_active']
    actions = ['send_email_invitation']
    add_form = CustomUserRegistrationForm
    add_fieldsets = ((
        None,
            {'fields':
                ('username', 'password1', 'password2', 'first_name', 'last_name', 'email'),
             }
        ),
    )

    def send_email_invitation(self, request, queryset):
        for user in queryset:
            if user.is_active == False: #email doesn't send unless user is active
                user.is_active = True
                user.save()
            reset_form = PasswordResetForm({'email': user.email}, request.POST)
            assert reset_form.is_valid()
            reset_form.save(
# subject_template_name='registration/account_creation_subject.txt',
# email_template_name='registration/invitation_email.html',
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

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
