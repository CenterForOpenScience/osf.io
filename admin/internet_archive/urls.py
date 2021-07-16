from django.conf.urls import url
from admin.internet_archive import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InternetArchiveView.as_view(), name='internet_archive'),
    url(r'^pigeon', views.SendToPigeon.as_view(), name='pigeon'),
    url(r'^create_ia_subcollections', views.CreateIASubcollections.as_view(), name='create_ia_subcollections'),
    url(r'^check_ia_metadata', views.CheckIAMetadata.as_view(), name='check_ia_metadata'),
    url(r'^sync_ia_metadata', views.SyncIAMetadata.as_view(), name='sync_ia_metadata'),
]
