from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^create/$', views.CreateCollectionProvider.as_view(), name='create'),
    re_path(r'^$', views.CollectionProviderList.as_view(), name='list'),
    re_path(r'^import/$', views.ImportCollectionProvider.as_view(), name='import'),
    re_path(r'^(?P<collection_provider_id>[a-z0-9]+)/$', views.CollectionProviderDetail.as_view(), name='detail'),
    re_path(r'^(?P<collection_provider_id>[a-z0-9]+)/delete/$', views.DeleteCollectionProvider.as_view(), name='delete'),
    re_path(r'^(?P<collection_provider_id>[a-z0-9]+)/export/$', views.ExportColectionProvider.as_view(), name='export'),
    re_path(r'^(?P<collection_provider_id>[a-z0-9]+)/import/$', views.ImportCollectionProvider.as_view(), name='import'),
    re_path(r'^(?P<collection_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
    re_path(r'^(?P<provider_id>[a-z0-9]+)/remove_admins_and_moderators/$', views.CollectionRemoveAdminsAndModerators.as_view(), name='remove_admins_and_moderators'),
    re_path(r'^(?P<provider_id>[a-z0-9]+)/add_admin_or_moderator/$', views.CollectionAddAdminOrModerator.as_view(), name='add_admin_or_moderator'),
]
