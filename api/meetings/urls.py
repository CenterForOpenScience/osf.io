from django.urls import re_path

from api.meetings import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.MeetingList.as_view(), name=views.MeetingList.view_name),
    re_path(r'^(?P<meeting_id>\w+)/$', views.MeetingDetail.as_view(), name=views.MeetingDetail.view_name),
    re_path(r'^(?P<meeting_id>\w+)/submissions/$', views.MeetingSubmissionList.as_view(), name=views.MeetingSubmissionList.view_name),
    re_path(r'^(?P<meeting_id>\w+)/submissions/(?P<submission_id>\w+)/$', views.MeetingSubmissionDetail.as_view(), name=views.MeetingSubmissionDetail.view_name),
]
