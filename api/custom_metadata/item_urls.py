from django.conf.urls import url

from api.custom_metadata import views

app_name = 'osf'

urlpatterns = [
    url(r'^osfio:(?P<guid_id>\w+)/$', views.CustomItemMetadataView.as_view(), name=views.CustomItemMetadataView.view_name),
]

