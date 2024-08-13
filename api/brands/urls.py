from django.urls import re_path

from api.brands import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.BrandList.as_view(), name=views.BrandList.view_name),
    re_path(r'^(?P<brand_id>\w+)/$', views.BrandDetail.as_view(), name=views.BrandDetail.view_name),
]
