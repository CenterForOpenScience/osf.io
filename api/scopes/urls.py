from django.conf.urls import url

from api.scopes import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.ScopeList.as_view(), name=views.ScopeList.view_name),
    url(r'^(?P<scope_id>[a-z0-9._]+)/$', views.ScopeDetail.as_view(), name=views.ScopeDetail.view_name),
]
