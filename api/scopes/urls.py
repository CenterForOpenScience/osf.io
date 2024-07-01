from django.urls import re_path

from api.scopes import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.ScopeList.as_view(), name=views.ScopeList.view_name),
    re_path(r'^(?P<scope_id>[a-z0-9._]+)/$', views.ScopeDetail.as_view(), name=views.ScopeDetail.view_name),
]
