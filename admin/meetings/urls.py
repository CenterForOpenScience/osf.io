from django.urls import re_path

from admin.meetings import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.MeetingListView.as_view(), name='list'),
    re_path(r'^create/$', views.MeetingCreateFormView.as_view(), name='create'),
    re_path(r'^(?P<endpoint>[a-zA-Z0-9_]+)/$', views.MeetingFormView.as_view(),
        name='detail'),
]
