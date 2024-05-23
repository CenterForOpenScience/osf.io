from django.urls import re_path

from api.resources import views

app_name = 'osf'

urlpatterns = [
    re_path(
        r'^$', views.ResourceList.as_view(), name=views.ResourceList.view_name,
    ),

    re_path(
        r'^(?P<resource_id>\w+)/$',
        views.ResourceDetail.as_view(),
        name=views.ResourceDetail.view_name,
    ),
]
