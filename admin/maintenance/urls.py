from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.MaintenanceDisplay.as_view(), name='display'),
    url(r'^remove/$', views.DeleteMaintenance.as_view(), name='delete'),
]
