from django.urls import re_path

from api.guids import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<guids>\w+)/$', views.GuidDetail.as_view(), name=views.GuidDetail.view_name),
]
