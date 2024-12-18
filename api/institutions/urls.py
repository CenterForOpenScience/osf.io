from django.urls import re_path

from api.institutions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.InstitutionList.as_view(), name=views.InstitutionList.view_name),
    re_path(r'^auth/$', views.InstitutionAuth.as_view(), name=views.InstitutionAuth.view_name),
    re_path(r'^(?P<institution_id>\w+)/$', views.InstitutionDetail.as_view(), name=views.InstitutionDetail.view_name),
    re_path(r'^(?P<institution_id>\w+)/nodes/$', views.InstitutionNodeList.as_view(), name=views.InstitutionNodeList.view_name),
    re_path(r'^(?P<institution_id>\w+)/registrations/$', views.InstitutionRegistrationList.as_view(), name=views.InstitutionRegistrationList.view_name),
    re_path(r'^(?P<institution_id>\w+)/relationships/registrations/$', views.InstitutionRegistrationsRelationship.as_view(), name=views.InstitutionRegistrationsRelationship.view_name),
    re_path(r'^(?P<institution_id>\w+)/relationships/nodes/$', views.InstitutionNodesRelationship.as_view(), name=views.InstitutionNodesRelationship.view_name),
    re_path(r'^(?P<institution_id>\w+)/users/$', views.InstitutionUserList.as_view(), name=views.InstitutionUserList.view_name),
    re_path(r'^(?P<institution_id>\w+)/metrics/summary/$', views.institution_summary_metrics_detail_view, name=views.institution_summary_metrics_detail_view.view_name),
    re_path(r'^(?P<institution_id>\w+)/metrics/departments/$', views.InstitutionDepartmentList.as_view(), name=views.InstitutionDepartmentList.view_name),
    re_path(r'^(?P<institution_id>\w+)/metrics/users/$', views.institution_user_metrics_list_view, name=views.institution_user_metrics_list_view.view_name),
]
