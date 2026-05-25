from django.urls import path, re_path

from api.files import views

app_name = 'osf'

urlpatterns = [

]

urlpatterns = [
    path('auth/', views.WaterbutlerAuthView.as_view(), name='WaterbutlerAuthView'),
    path('project/<str:pid>/waterbutler/logs/', views.WaterbutlerLogView.as_view(), name='waterbutler-logs-project'),
    path('project/<str:pid>/node/<str:nid>/waterbutler/logs/', views.WaterbutlerLogView.as_view(), name='waterbutler-logs-node'),

    re_path(r'^(?P<file_id>\w+)/$', views.FileDetail.as_view(), name=views.FileDetail.view_name),
    re_path(r'^(?P<file_id>\w+)/cedar_metadata_records/$', views.FileCedarMetadataRecordsList.as_view(), name=views.FileCedarMetadataRecordsList.view_name),
    re_path(r'^(?P<file_id>\w+)/versions/$', views.FileVersionsList.as_view(), name=views.FileVersionsList.view_name),
    re_path(r'^(?P<file_id>\w+)/versions/(?P<version_id>\w+)/$', views.FileVersionDetail.as_view(), name=views.FileVersionDetail.view_name),
]
