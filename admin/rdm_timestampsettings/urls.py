from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='institutions'),
    url(r'^force/(?P<institution_id>[0-9]+)/(?P<timestamp_pattern_division>[0-9])/(?P<forced>[01])$',
        views.InstitutionTimeStampPatternForce.as_view(), name='institutionsforce'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/change/(?P<guid>[a-z0-9]+)/(?P<timestamp_pattern_division>[0-9])$',
        views.NodeTimeStampPatternChange.as_view(), name='nodeforce'),
]
