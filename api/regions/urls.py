from django.urls import re_path

from api.regions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.RegionList.as_view(), name=views.RegionList.view_name),
    re_path(r'^(?P<region_id>[-\w]+)/$', views.RegionDetail.as_view(), name=views.RegionDetail.view_name),
]
