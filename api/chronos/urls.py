from django.urls import re_path

from api.chronos import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^journals/$', views.ChronosJournalList.as_view(), name=views.ChronosJournalList.view_name),
    re_path(r'^journals/(?P<journal_id>[-0-9A-Za-z]+)/$', views.ChronosJournalDetail.as_view(), name=views.ChronosJournalDetail.view_name),
    re_path(r'^(?P<preprint_id>\w+)/submissions/$', views.ChronosSubmissionList.as_view(), name=views.ChronosSubmissionList.view_name),
    re_path(r'^(?P<preprint_id>\w+)/submissions/(?P<submission_id>[-0-9A-Za-z]+)/$', views.ChronosSubmissionDetail.as_view(), name=views.ChronosSubmissionDetail.view_name),
]
