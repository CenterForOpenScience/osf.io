from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^create/$', views.CreateRegistrationProvider.as_view(), name='create'),
    url(r'^$', views.RegistrationProviderList.as_view(), name='list'),
    url(r'^import/$', views.ImportRegistrationProvider.as_view(), name='import'),
    url(r'^process_custom_taxonomy/$', views.ProcessCustomTaxonomy.as_view(), name='process_custom_taxonomy'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/$', views.RegistrationProviderDetail.as_view(), name='detail'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/delete/$', views.DeleteRegistrationProvider.as_view(), name='delete'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/export/$', views.ExportRegistrationProvider.as_view(), name='export'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/import/$', views.ImportRegistrationProvider.as_view(), name='import'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/schemas/$', views.ChangeSchema.as_view(), name='schemas'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/share_source/$', views.ShareSourceRegistrationProvider.as_view(), name='share_source'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/remove_admins_and_moderators/$', views.RemoveAdminsAndModerators.as_view(), name='remove_admins_and_moderators'),
    url(r'^(?P<registration_provider_id>[a-z0-9]+)/add_admin_or_moderator/$', views.AddAdminOrModerator.as_view(), name='add_admin_or_moderator'),
]
