from django.conf.urls import url
from api.wb import views

app_name = 'osf'

urlpatterns = [
    url(r'^hooks/(?P<node_id>\w+)/move/', views.MoveFile.as_view(), name=views.MoveFile.view_name),
    url(r'^hooks/(?P<node_id>\w+)/copy/', views.MoveFile.as_view(), name=views.MoveFile.view_name),
]
