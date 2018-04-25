
from django.conf.urls import url

from api.storage_regions import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.StorageRegionList.as_view(), name=views.StorageRegionList.view_name),
    url(r'^^(?P<region_id>[-\w]+)/$', views.StorageRegionDetail.as_view(), name=views.StorageRegionDetail.view_name),
]
