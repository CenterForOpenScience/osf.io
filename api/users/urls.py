from django.conf.urls import url
from . import views

from osf.quickfiles.views import UserQuickFiles

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.UserList.as_view(), name=views.UserList.view_name),
    url(r'^(?P<user_id>\w+)/$', views.UserDetail.as_view(), name=views.UserDetail.view_name),
    url(r'^(?P<user_id>\w+)/addons/$', views.UserAddonList.as_view(), name=views.UserAddonList.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/$', views.UserAddonDetail.as_view(), name=views.UserAddonDetail.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/accounts/$', views.UserAddonAccountList.as_view(), name=views.UserAddonAccountList.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/accounts/(?P<account_id>\w+)/$', views.UserAddonAccountDetail.as_view(), name=views.UserAddonAccountDetail.view_name),
    url(r'^(?P<user_id>\w+)/claim/$', views.ClaimUser.as_view(), name=views.ClaimUser.view_name),
    url(r'^(?P<user_id>\w+)/draft_registrations/$', views.UserDraftRegistrations.as_view(), name=views.UserDraftRegistrations.view_name),
    url(r'^(?P<user_id>\w+)/institutions/$', views.UserInstitutions.as_view(), name=views.UserInstitutions.view_name),
    url(r'^(?P<user_id>\w+)/nodes/$', views.UserNodes.as_view(), name=views.UserNodes.view_name),
    url(r'^(?P<user_id>\w+)/preprints/$', views.UserPreprints.as_view(), name=views.UserPreprints.view_name),
    url(r'^(?P<user_id>\w+)/registrations/$', views.UserRegistrations.as_view(), name=views.UserRegistrations.view_name),
    url(r'^(?P<user_id>\w+)/settings/$', views.UserSettings.as_view(), name=views.UserSettings.view_name),
    url(r'^(?P<user_id>\w+)/quickfiles/$', UserQuickFiles.as_view(), name=UserQuickFiles.view_name),
    url(r'^(?P<user_id>\w+)/relationships/institutions/$', views.UserInstitutionsRelationship.as_view(), name=views.UserInstitutionsRelationship.view_name),
    url(r'^(?P<user_id>\w+)/settings/emails/$', views.UserEmailsList.as_view(), name=views.UserEmailsList.view_name),
    url(r'^(?P<user_id>\w+)/settings/emails/(?P<email_id>\w+)/$', views.UserEmailsDetail.as_view(), name=views.UserEmailsDetail.view_name),
    url(r'^(?P<user_id>\w+)/settings/identities/$', views.UserIdentitiesList.as_view(), name=views.UserIdentitiesList.view_name),
    url(r'^(?P<user_id>\w+)/settings/identities/(?P<identity_id>\w+)/$', views.UserIdentitiesDetail.as_view(), name=views.UserIdentitiesDetail.view_name),
    url(r'^(?P<user_id>\w+)/settings/export/$', views.UserAccountExport.as_view(), name=views.UserAccountExport.view_name),
    url(r'^(?P<user_id>\w+)/settings/password/$', views.UserChangePassword.as_view(), name=views.UserChangePassword.view_name),
]
