from __future__ import absolute_import

from django.conf.urls import url

from admin.meetings import views

urlpatterns = [
    url(r'^$', views.MeetingListView.as_view(), name='list'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.MeetingFormView.as_view(),
        name='detail'),
    url(r'^create/$', views.MeetingFormView.as_view(), name='create'),
]
