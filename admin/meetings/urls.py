from __future__ import absolute_import

from django.conf.urls import url

from admin.meetings import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.MeetingListView.as_view(), name='list'),
    url(r'^create/$', views.MeetingCreateFormView.as_view(), name='create'),
    url(r'^(?P<endpoint>[a-zA-Z0-9_]+)/$', views.MeetingFormView.as_view(),
        name='detail'),
]
