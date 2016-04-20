from __future__ import absolute_import

from django.conf.urls import url

from admin.meetings import views

urlpatterns = [
    url(r'^$', views, name='list'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views, name='detail'),
    url(r'^(?P<guid>[a-z0-9]+)/edit/$', views, name='edit'),
    url(r'^create/$', views, name='create'),
]
