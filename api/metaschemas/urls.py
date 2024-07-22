from django.urls import re_path

from api.metaschemas import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.DeprecatedMetaSchemasList.as_view(), name=views.DeprecatedMetaSchemasList.view_name),
    re_path(r'^registrations/$', views.DeprecatedRegistrationMetaSchemaList.as_view(), name=views.DeprecatedRegistrationMetaSchemaList.view_name),
    re_path(r'^(?P<metaschema_id>\w+)/$', views.DeprecatedMetaSchemaDetail.as_view(), name=views.DeprecatedMetaSchemaDetail.view_name),
    re_path(r'^registrations/(?P<schema_id>\w+)/$', views.DeprecatedRegistrationMetaSchemaDetail.as_view(), name=views.DeprecatedRegistrationMetaSchemaDetail.view_name),
]
