from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.UserIdentificationAdminListView.as_view(),
        name='user_identification_list'),
    url(r'^csvexport/$', views.ExportFileCSVAdminView.as_view(),
        name='user_identification_export_csv'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserIdentificationDetailAdminView.as_view(),
        name='user_identification_detail'),
]
