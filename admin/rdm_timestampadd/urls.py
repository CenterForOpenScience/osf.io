from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='institutions'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/$',
        views.TimeStampAddList.as_view(), name='timestamp_add'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/verify/$',
        views.VerifyTimestamp.as_view(), name='verify'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/add_timestamp_data/$',
        views.AddTimestamp.as_view(), name='add_timestamp_data'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/cancel_task/$',
        views.CancelTask.as_view(), name='cancel_task'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/task_status/$',
        views.TaskStatus.as_view(), name='task_status'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/download_errors/$',
        views.DownloadErrors.as_view(), name='download_errors'),
]
