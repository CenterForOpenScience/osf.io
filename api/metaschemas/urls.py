from django.conf.urls import url

from api.metaschemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.MetaSchemasList.as_view(), name=views.MetaSchemasList.view_name),
    url(r'^(?P<metaschema_id>\w+)/$', views.MetaSchemaDetail.as_view(), name=views.MetaSchemaDetail.view_name)
]
