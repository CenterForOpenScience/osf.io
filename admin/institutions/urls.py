from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='list'),
    url(r'^create/$', views.CreateInstitution.as_view(), name='create'),
    url(r'^import/$', views.ImportInstitution.as_view(), name='import'),
    url(r'^(?P<institution_id>[0-9]+)/$', views.InstitutionDetail.as_view(), name='detail'),
    url(r'^(?P<institution_id>[0-9]+)/export/$', views.InstitutionExport.as_view(), name='export'),
    url(r'^(?P<institution_id>[0-9]+)/delete/$', views.DeleteInstitution.as_view(), name='delete'),
    url(r'^(?P<institution_id>[0-9]+)/deactivate/$', views.DeactivateInstitution.as_view(), name='deactivate'),
    url(r'^(?P<institution_id>[0-9]+)/reactivate/$', views.ReactivateInstitution.as_view(), name='reactivate'),
    url(r'^(?P<institution_id>[0-9]+)/cannot_delete/$', views.CannotDeleteInstitution.as_view(), name='cannot_delete'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    url(r'^(?P<institution_id>[0-9]+)/register/$', views.InstitutionalMetricsAdminRegister.as_view(), name='register_metrics_admin'),
]
