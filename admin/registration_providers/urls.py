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
]
