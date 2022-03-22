from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.UserEmailsFormView.as_view(), name='search'),
    url(r'^search/name/(?P<name>.*)/$', views.UserEmailsSearchList.as_view(), name='search_list'),
    url(r'^search/guid/(?P<guid>[a-z0-9]+)/$', views.UserEmailsSearchList.as_view(), name='search_list_guid'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserEmailsView.as_view(), name='user'),
    url(r'^(?P<guid>[a-z0-9]+)/primary/$', views.UserPrimaryEmail.as_view(), name='primary'),
]
