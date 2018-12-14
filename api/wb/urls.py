from django.conf.urls import url
from api.wb import views

app_name = 'osf'

urlpatterns = [
    url(r'^hooks/(?P<target_id>\w+)/move/', views.MoveFileMetadataView.as_view(), name=views.MoveFileMetadataView.view_name),
    url(r'^hooks/(?P<target_id>\w+)/copy/', views.CopyFileMetadataView.as_view(), name=views.CopyFileMetadataView.view_name),
]
