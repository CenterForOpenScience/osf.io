from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^institutions/$', views.UserIdentificationInstitutionListView.as_view(),
        name='user_identification_institutions'),
    url(r'^institutions/(?P<institution_id>[0-9]+)/$', views.UserIdentificationListView.as_view(),
        name='user_identification_list'),
    url(r'^institutions/(?P<institution_id>[0-9]+)/csvexport/$', views.ExportFileCSVView.as_view(),
        name='user_identification_export_csv'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserIdentificationDetailView.as_view(),
        name='user_identification_detail'),
]
