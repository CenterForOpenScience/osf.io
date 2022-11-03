from django.urls import path

from api.custom_metadata import views

app_name = 'osf'

urlpatterns = [
    path('osfio:<guid_id>/', views.CustomFileMetadataDetail.as_view(), name=views.CustomFileMetadataDetail.view_name),
]
