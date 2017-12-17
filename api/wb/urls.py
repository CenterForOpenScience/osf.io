from django.conf.urls import url
from api.wb import views

app_name = 'osf'

urlpatterns = [
    url(r'^hooks/(?P<node_id>\w+)/move/', views.MoveFileMetadata.as_view(), name=views.MoveFileMetadata.view_name),
    url(r'^hooks/(?P<node_id>\w+)/copy/', views.MoveFileMetadata.as_view(), name=views.MoveFileMetadata.view_name),
]
