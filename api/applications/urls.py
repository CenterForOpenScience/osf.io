from django.urls import re_path

from api.applications import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.ApplicationList.as_view(), name=views.ApplicationList.view_name),
    re_path(r'^(?P<client_id>\w+)/$', views.ApplicationDetail.as_view(), name=views.ApplicationDetail.view_name),
    re_path(r'^(?P<client_id>\w+)/reset/$', views.ApplicationReset.as_view(), name=views.ApplicationReset.view_name),
]
