from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.ProjectLimitNumberSettingListView.as_view(), name='list-setting'),
    url(r'^create/$', views.ProjectLimitNumberSettingCreateView.as_view(), name='create-setting'),
    url(r'^update/$', views.ProjectLimitNumberSettingSaveAvailabilityView.as_view(), name='save-settings-availability'),
    url(r'^delete/(?P<setting_id>[0-9]+)/$', views.DeleteProjectLimitNumberSettingView.as_view(), name='delete-setting'),
    url(r'^project_number_default$', views.SaveProjectLimitNumberDefaultView.as_view(), name='save-project-number-default'),
    url(r'^(?P<setting_id>[0-9]+)/$', views.ProjectLimitNumberSettingDetailView.as_view(), name='setting-detail'),
    url(r'^(?P<setting_id>[0-9]+)/update/$', views.UpdateProjectLimitNumberSettingView.as_view(), name='update-setting'),
    url(r'^user_list/$', views.UserListView.as_view(), name='user_list'),
]
