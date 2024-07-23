from django.urls import re_path

from api.schema_responses import views

app_name = 'osf'

urlpatterns = [
    re_path(
        r'^$', views.SchemaResponseList.as_view(), name=views.SchemaResponseList.view_name,
    ),
    re_path(
        r'^(?P<schema_response_id>\w+)/$',
        views.SchemaResponseDetail.as_view(),
        name=views.SchemaResponseDetail.view_name,
    ),
    re_path(
        r'^(?P<schema_response_id>\w+)/actions/$', views.SchemaResponseActionList.as_view(),
        name=views.SchemaResponseActionList.view_name,
    ),
    re_path(
        r'^(?P<schema_response_id>\w+)/actions/(?P<schema_response_action_id>\w+)/$', views.SchemaResponseActionDetail.as_view(),
        name=views.SchemaResponseActionDetail.view_name,
    ),
]
