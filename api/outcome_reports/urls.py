from django.conf.urls import url

from api.schema_response import views

app_name = "osf"

urlpatterns = [
    url(
        r"^$", views.SchemaResponsesList.as_view(), name=views.SchemaResponsesList.view_name
    ),
    url(
        r"^(?P<report_id>\w+)/$",
        views.SchemaResponsesDetail.as_view(),
        name=views.SchemaResponsesDetail.view_name,
    ),
    url(
        r"^(?P<report_id>\w+)/versions/$",
        views.SchemaResponsesVersions.as_view(),
        name=views.SchemaResponseVersions.view_name,
    ),
]
