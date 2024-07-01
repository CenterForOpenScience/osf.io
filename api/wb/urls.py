from django.urls import re_path
from api.wb import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^hooks/(?P<target_id>\w+)/move/', views.MoveFileMetadataView.as_view(), name=views.MoveFileMetadataView.view_name),
    re_path(r'^hooks/(?P<target_id>\w+)/copy/', views.CopyFileMetadataView.as_view(), name=views.CopyFileMetadataView.view_name),
]
