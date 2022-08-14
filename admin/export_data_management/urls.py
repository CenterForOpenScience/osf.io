from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.ExportDataManagement.as_view(), name='list_export_data_management'),
    url(r'^restore_export_data$', views.ExportDataRestore.as_view(), name='export_data_restore'),
    url(r'^task_status$', views.ExportDataRestoreTaskStatus.as_view(), name='export_data_restore_task_status'),
]
