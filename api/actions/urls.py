from django.urls import re_path

from . import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^reviews/$', views.ReviewActionListCreate.as_view(), name=views.ReviewActionListCreate.view_name),
    re_path(r'^requests/nodes/$', views.NodeRequestActionCreate.as_view(), name=views.NodeRequestActionCreate.view_name),
    re_path(r'^requests/preprints/$', views.PreprintRequestActionCreate.as_view(), name=views.NodeRequestActionCreate.view_name),
    re_path(r'^(?P<action_id>\w+)/$', views.ActionDetail.as_view(), name=views.ActionDetail.view_name),
]
