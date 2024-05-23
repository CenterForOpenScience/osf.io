from django.urls import re_path
from . import views
from admin.providers.views import AddAdminOrModerator, RemoveAdminsAndModerators

app_name = 'admin'

urlpatterns = [
    re_path(r'^create/$', views.CreateRegistrationProvider.as_view(), name='create'),
    re_path(r'^$', views.RegistrationProviderList.as_view(), name='list'),
    re_path(r'^import/$', views.ImportRegistrationProvider.as_view(), name='import'),
    re_path(r'^process_custom_taxonomy/$', views.ProcessCustomTaxonomy.as_view(), name='process_custom_taxonomy'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/$', views.RegistrationProviderDetail.as_view(), name='detail'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/delete/$', views.DeleteRegistrationProvider.as_view(), name='delete'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/export/$', views.ExportRegistrationProvider.as_view(), name='export'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/import/$', views.ImportRegistrationProvider.as_view(), name='import'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/schemas/$', views.ChangeSchema.as_view(), name='schemas'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
    re_path(r'^(?P<registration_provider_id>[a-z0-9]+)/share_source/$', views.ShareSourceRegistrationProvider.as_view(), name='share_source'),
    re_path(r'^(?P<provider_id>[a-z0-9]+)/remove_admins_and_moderators/$', RemoveAdminsAndModerators.as_view(), name='remove_admins_and_moderators'),
    re_path(r'^(?P<provider_id>[a-z0-9]+)/add_admin_or_moderator/$', AddAdminOrModerator.as_view(), name='add_admin_or_moderator'),
]
