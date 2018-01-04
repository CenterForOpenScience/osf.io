from django.conf.urls import url
from . import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.UserList.as_view(), name=views.UserList.view_name),
    url(r'^(?P<user_id>\w+)/$', views.UserDetail.as_view(), name=views.UserDetail.view_name),
    url(r'^(?P<user_id>\w+)/addons/$', views.UserAddonList.as_view(), name=views.UserAddonList.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/$', views.UserAddonDetail.as_view(), name=views.UserAddonDetail.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/accounts/$', views.UserAddonAccountList.as_view(), name=views.UserAddonAccountList.view_name),
    url(r'^(?P<user_id>\w+)/addons/(?P<provider>\w+)/accounts/(?P<account_id>\w+)/$', views.UserAddonAccountDetail.as_view(), name=views.UserAddonAccountDetail.view_name),
    url(r'^(?P<user_id>\w+)/institutions/$', views.UserInstitutions.as_view(), name=views.UserInstitutions.view_name),
    url(r'^(?P<user_id>\w+)/nodes/$', views.UserNodes.as_view(), name=views.UserNodes.view_name),
    url(r'^(?P<user_id>\w+)/preprints/$', views.UserPreprints.as_view(), name=views.UserPreprints.view_name),
    url(r'^(?P<user_id>\w+)/registrations/$', views.UserRegistrations.as_view(), name=views.UserRegistrations.view_name),
    url(r'^(?P<user_id>\w+)/quickfiles/$', views.UserQuickFiles.as_view(), name=views.UserQuickFiles.view_name),
    url(r'^(?P<user_id>\w+)/relationships/institutions/$', views.UserInstitutionsRelationship.as_view(), name=views.UserInstitutionsRelationship.view_name),
]
