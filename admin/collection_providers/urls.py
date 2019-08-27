from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^create/$', views.CreateCollectionProvider.as_view(), name='create'),
    url(r'^$', views.CollectionProviderList.as_view(), name='list'),
    url(r'^import/$', views.ImportCollectionProvider.as_view(), name='import'),
    url(r'^(?P<collection_provider_id>[a-z0-9]+)/$', views.CollectionProviderDetail.as_view(), name='detail'),
    url(r'^(?P<collection_provider_id>[a-z0-9]+)/delete/$', views.DeleteCollectionProvider.as_view(), name='delete'),
    url(r'^(?P<collection_provider_id>[a-z0-9]+)/export/$', views.ExportColectionProvider.as_view(), name='export'),
    url(r'^(?P<collection_provider_id>[a-z0-9]+)/import/$', views.ImportCollectionProvider.as_view(), name='import'),
    url(r'^(?P<collection_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
]
