from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.MaintenanceDisplay.as_view(), name='display'),
    re_path(r'^remove/$', views.DeleteMaintenance.as_view(), name='delete'),
]
