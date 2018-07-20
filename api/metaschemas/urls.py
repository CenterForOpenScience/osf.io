from django.conf.urls import url

from api.metaschemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.DeprecatedMetaSchemasList.as_view(), name=views.DeprecatedMetaSchemasList.view_name),
    url(r'^registrations/$', views.RegistrationMetaschemaList.as_view(), name=views.RegistrationMetaschemaList.view_name),
    url(r'^(?P<metaschema_id>\w+)/$', views.DeprecatedMetaSchemaDetail.as_view(), name=views.DeprecatedMetaSchemaDetail.view_name),
    url(r'^registrations/(?P<metaschema_id>\w+)/$', views.RegistrationMetaschemaDetail.as_view(), name=views.RegistrationMetaschemaDetail.view_name),
]
