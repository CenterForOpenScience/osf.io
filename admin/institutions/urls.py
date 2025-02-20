from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionList.as_view(), name='list'),
    re_path(r'^create/$', views.CreateInstitution.as_view(), name='create'),
    re_path(r'^import/$', views.ImportInstitution.as_view(), name='import'),
    re_path(r'^(?P<institution_id>[0-9]+)/$', views.InstitutionDetail.as_view(), name='detail'),
    re_path(r'^(?P<institution_id>[0-9]+)/export/$', views.InstitutionExport.as_view(), name='export'),
    re_path(r'^(?P<institution_id>[0-9]+)/delete/$', views.DeleteInstitution.as_view(), name='delete'),
    re_path(r'^(?P<institution_id>[0-9]+)/deactivate/$', views.DeactivateInstitution.as_view(), name='deactivate'),
    re_path(r'^(?P<institution_id>[0-9]+)/reactivate/$', views.ReactivateInstitution.as_view(), name='reactivate'),
    re_path(r'^(?P<institution_id>[0-9]+)/cannot_delete/$', views.CannotDeleteInstitution.as_view(), name='cannot_delete'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    re_path(r'^(?P<institution_id>[0-9]+)/register/$', views.InstitutionalMetricsAdminRegister.as_view(), name='register_metrics_admin'),
]
