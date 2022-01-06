from django.conf.urls import url

from api.schemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^registrations/$', views.RegistrationSchemaList.as_view(), name=views.RegistrationSchemaList.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/$', views.RegistrationSchemaDetail.as_view(), name=views.RegistrationSchemaDetail.view_name),
    url(r'^files/$', views.FileSchemaList.as_view(), name=views.FileSchemaList.view_name),
    url(r'^files/(?P<schema_id>\w+)/$', views.FileSchemaDetail.as_view(), name=views.FileSchemaDetail.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/schema_blocks/$', views.RegistrationSchemaBlocks.as_view(), name=views.RegistrationSchemaBlocks.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/schema_blocks/(?P<schema_block_id>\w+)/$', views.RegistrationSchemaBlockDetail.as_view(), name=views.RegistrationSchemaBlockDetail.view_name),
]
