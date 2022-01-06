from django.conf.urls import url

from api.registration_schema_responses import views

app_name = 'osf'

urlpatterns = [
    url(
        r'^$', views.SchemaResponseList.as_view(), name=views.SchemaResponseList.view_name,
    ),
    url(
        r'^(?P<schema_response_id>\w+)/$',
        views.SchemaResponseDetail.as_view(),
        name=views.SchemaResponseDetail.view_name,
    ),
    url(
        r'^(?P<schema_response_id>\w+)/actions/$', views.SchemaResponseActionList.as_view(),
        name=views.SchemaResponseActionList.view_name,
    ),
    url(
        r'^(?P<schema_response_id>\w+)/actions/(?P<schema_response_action_id>\w+)/$', views.SchemaResponseActionDetail.as_view(),
        name=views.SchemaResponseActionDetail.view_name,
    ),
]
