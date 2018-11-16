from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='institutions'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/$',
        views.TimeStampAddList.as_view(), name='timestamp_add'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/verify/$',
        views.VerifyTimeStampAddList.as_view(), name='verify'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/verify/verify_data/$',
        views.TimestampVerifyData.as_view(), name='verify_data'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/$',
        views.AddTimeStampResultList.as_view(), name='addtimestamp'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/add_timestamp_data/$',
        views.AddTimestampData.as_view(), name='add_timestamp_data'),
]
