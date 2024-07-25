from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^(?P<request_id>\w+)/$', views.RequestDetail.as_view(), name=views.RequestDetail.view_name),
    re_path(r'^(?P<request_id>\w+)/actions/$', views.RequestActionList.as_view(), name=views.RequestActionList.view_name),
]
