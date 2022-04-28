from django.conf.urls import url
from . import views
from admin.entitlements.views import InstitutionEntitlementList, ToggleInstitutionEntitlement, DeleteInstitutionEntitlement

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='list'),
    url(r'^institution_list/$', views.InstitutionUserList.as_view(), name='institution_list'),
    url(r'^create/$', views.CreateInstitution.as_view(), name='create'),
    url(r'^import/$', views.ImportInstitution.as_view(), name='import'),
    url(r'^entitlements/$', InstitutionEntitlementList.as_view(), name='entitlements'),
    # url(r'^(?P<institution_id>[0-9]+)/entitlements/$', InstitutionEntitlementList.as_view(), name='inst_entitlements'),
    url(r'^(?P<institution_id>[0-9]+)/entitlements/(?P<entitlement_id>[0-9]+)/toggle/$', ToggleInstitutionEntitlement.as_view(), name='entitlement_toggle'),
    url(r'^(?P<institution_id>[0-9]+)/entitlements/(?P<entitlement_id>[0-9]+)/delete/$', DeleteInstitutionEntitlement.as_view(), name='entitlement_delete'),
    url(r'^(?P<institution_id>[0-9]+)/$', views.InstitutionDetail.as_view(), name='detail'),
    url(r'^(?P<institution_id>[0-9]+)/export/$', views.InstitutionExport.as_view(), name='export'),
    url(r'^(?P<institution_id>[0-9]+)/delete/$', views.DeleteInstitution.as_view(), name='delete'),
    url(r'^(?P<institution_id>[0-9]+)/cannot_delete/$', views.CannotDeleteInstitution.as_view(), name='cannot_delete'),
    url(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    url(r'^(?P<institution_id>[0-9]+)/register/$', views.InstitutionalMetricsAdminRegister.as_view(), name='register_metrics_admin'),
    url(r'^(?P<institution_id>[0-9]+)/update_quota/$', views.UpdateQuotaUserListByInstitutionID.as_view(), name='update_quota_institution_user_list'),
    url(r'^(?P<institution_id>[0-9]+)/tsvexport/$', views.ExportFileTSV.as_view(), name='tsvexport'),
    url(r'^user_list_by_institution_id/(?P<institution_id>[0-9]+)/.*$', views.UserListByInstitutionID.as_view(), name='institution_user_list'),
    url(r'^statistical_status_default_storage/$', views.StatisticalStatusDefaultStorage.as_view(), name='statistical_status_default_storage'),
    url(r'^recalculate_quota/$', views.RecalculateQuota.as_view(), name='recalculate_quota'),
    url(r'^recalculate_quota_of_users_in_institution/$',
        views.RecalculateQuotaOfUsersInInstitution.as_view(), name='recalculate_quota_of_users_in_institution'),
]
