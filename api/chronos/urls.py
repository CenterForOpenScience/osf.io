from django.conf.urls import url

from api.chronos import views

app_name = 'osf'

urlpatterns = [
    url(r'^journals/$', views.ChronosJournalList.as_view(), name=views.ChronosJournalList.view_name),
    url(r'^journals/(?P<journal_id>[0-9]{4}-[0-9]{4})/$', views.ChronosJournalDetail.as_view(), name=views.ChronosJournalDetail.view_name),
    url(r'^(?P<preprint_id>\w+)/submissions/$', views.ChronosSubmissionList.as_view(), name=views.ChronosSubmissionList.view_name),
    url(r'^(?P<preprint_id>\w+)/submissions/(?P<submission_id>\w+)/$', views.ChronosSubmissionDetail.as_view(), name=views.ChronosSubmissionDetail.view_name),
]
