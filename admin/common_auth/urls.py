from django.urls import re_path

from admin.common_auth import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^login/?$', views.LoginView.as_view(), name='login'),
    re_path(r'^logout/$', views.logout_user, name='logout'),
    re_path(r'^register/$', views.RegisterUser.as_view(), name='register'),
    re_path(r'^audit/$', views.AdminUserAudit.as_view(), name='admin_audit'),
    re_path(r'^audit/(?P<guid>[a-z0-9]+)/staff/$', views.AdminUserStaffChange.as_view(), name='admin_audit_staff'),
    re_path(r'^audit/(?P<guid>[a-z0-9]+)/revoke_superuser/$', views.AdminUserSuperuserRevoke.as_view(), name='admin_audit_revoke_superuser'),
    re_path(r'^settings/desk/$', views.DeskUserCreateFormView.as_view(), name='desk'),
    re_path(r'^settings/desk/update/$', views.DeskUserUpdateFormView.as_view(), name='desk_update'),
]
