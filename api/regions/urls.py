
from django.conf.urls import url

from api.regions import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.RegionList.as_view(), name=views.RegionList.view_name),
    url(r'^(?P<region_id>[-\w]+)/$', views.RegionDetail.as_view(), name=views.RegionDetail.view_name),
]
