from django.urls import path

from api.custom_metadata import views

app_name = "osf"

urlpatterns = [
    path(
        "<guid_id>/",
        views.CustomItemMetadataDetail.as_view(),
        name=views.CustomItemMetadataDetail.view_name,
    ),
]
