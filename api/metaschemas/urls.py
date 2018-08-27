from django.conf.urls import url

from api.metaschemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.DeprecatedMetaSchemasList.as_view(), name=views.DeprecatedMetaSchemasList.view_name),
    url(r'^registrations/$', views.DeprecatedRegistrationMetaSchemaList.as_view(), name=views.DeprecatedRegistrationMetaSchemaList.view_name),
    url(r'^(?P<metaschema_id>\w+)/$', views.DeprecatedMetaSchemaDetail.as_view(), name=views.DeprecatedMetaSchemaDetail.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/$', views.DeprecatedRegistrationMetaSchemaDetail.as_view(), name=views.DeprecatedRegistrationMetaSchemaDetail.view_name),
]
