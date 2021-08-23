from django.conf.urls import url

from api.institutions import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name=views.InstitutionList.view_name),
    url(r'^auth/$', views.InstitutionAuth.as_view(), name=views.InstitutionAuth.view_name),
    url(r'^(?P<institution_id>\w+)/$', views.InstitutionDetail.as_view(), name=views.InstitutionDetail.view_name),
    url(r'^(?P<institution_id>\w+)/nodes/$', views.InstitutionNodeList.as_view(), name=views.InstitutionNodeList.view_name),
    url(r'^(?P<institution_id>\w+)/registrations/$', views.InstitutionRegistrationList.as_view(), name=views.InstitutionRegistrationList.view_name),
    url(r'^(?P<institution_id>\w+)/relationships/registrations/$', views.InstitutionRegistrationsRelationship.as_view(), name=views.InstitutionRegistrationsRelationship.view_name),
    url(r'^(?P<institution_id>\w+)/relationships/nodes/$', views.InstitutionNodesRelationship.as_view(), name=views.InstitutionNodesRelationship.view_name),
    url(r'^(?P<institution_id>\w+)/users/$', views.InstitutionUserList.as_view(), name=views.InstitutionUserList.view_name),
    url(r'^(?P<institution_id>\w+)/metrics/summary/$', views.InstitutionSummaryMetrics.as_view(), name=views.InstitutionSummaryMetrics.view_name),
    url(r'^(?P<institution_id>\w+)/metrics/departments/$', views.InstitutionDepartmentList.as_view(), name=views.InstitutionDepartmentList.view_name),
    url(r'^(?P<institution_id>\w+)/metrics/users/$', views.InstitutionUserMetricsList.as_view(), name=views.InstitutionUserMetricsList.view_name),
]
