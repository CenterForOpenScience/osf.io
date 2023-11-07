from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InstitutionStorageList.as_view(), name='list_institution_storage'),
    url(r'^(?P<institution_id>[0-9]+)/update_quota/$', views.UpdateQuotaUserListByInstitutionStorageID.as_view(), name='update_quota_institution_user_list'),
    url(r'^user_list_by_institution_id/(?P<institution_id>.*)/$', views.UserListByInstitutionStorageID.as_view(), name='institution_user_list'),
]
