from django.conf.urls import url

from api.institutions import views

urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name=views.InstitutionList.view_name),
    url(r'^(?P<institution_id>\w+)/$', views.InstitutionDetail.as_view(), name=views.InstitutionDetail.view_name),
    url(r'^(?P<institution_id>\w+)/nodes/$', views.InstitutionNodeList.as_view(), name=views.InstitutionNodeList.view_name),
    url(r'^(?P<institution_id>\w+)/nodes/(?P<node_id>\w+)/$', views.InstitutionNodeDetail.as_view(), name=views.InstitutionNodeDetail.view_name),
    url(r'^(?P<institution_id>\w+)/users/$', views.InstitutionUserList.as_view(), name=views.InstitutionUserList.view_name),
    url(r'^(?P<institution_id>\w+)/users/(?P<user_id>\w+)/$', views.InstitutionUserDetail.as_view(), name=views.InstitutionUserDetail.view_name),
]

