from django.conf.urls import url

from api.schemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^registrations/$', views.RegistrationSchemaList.as_view(), name=views.RegistrationSchemaList.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/$', views.RegistrationSchemaDetail.as_view(), name=views.RegistrationSchemaDetail.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/form_blocks/$', views.RegistrationSchemaFormBlocks.as_view(), name=views.RegistrationSchemaFormBlocks.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/form_blocks/(?P<form_block_id>\w+)/$', views.RegistrationSchemaFormBlockDetail.as_view(), name=views.RegistrationSchemaFormBlockDetail.view_name),
]
