from django.urls import re_path
from admin.internet_archive import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InternetArchiveView.as_view(), name='internet_archive'),
    re_path(r'^pigeon', views.SendToPigeon.as_view(), name='pigeon'),
    re_path(r'^create_ia_subcollections', views.CreateIASubcollections.as_view(), name='create_ia_subcollections'),
    re_path(r'^check_ia_metadata', views.CheckIAMetadata.as_view(), name='check_ia_metadata'),
    re_path(r'^sync_ia_metadata', views.SyncIAMetadata.as_view(), name='sync_ia_metadata'),
]
