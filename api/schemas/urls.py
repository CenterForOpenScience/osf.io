from django.conf.urls import url

from api.schemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.DeprecatedMetaSchemasList.as_view(), name=views.DeprecatedMetaSchemasList.view_name),
    url(r'^registrations/$', views.RegistrationSchemaList.as_view(), name=views.RegistrationSchemaList.view_name),
    url(r'^(?P<metaschema_id>\w+)/$', views.DeprecatedMetaSchemaDetail.as_view(), name=views.DeprecatedMetaSchemaDetail.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/$', views.RegistrationSchemaDetail.as_view(), name=views.RegistrationSchemaDetail.view_name),
]
