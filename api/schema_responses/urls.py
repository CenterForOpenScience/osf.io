from django.conf.urls import url

from api.schema_responses import views

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
]
