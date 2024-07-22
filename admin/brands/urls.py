from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.BrandList.as_view(), name='list'),
    re_path(r'^create/$', views.BrandCreate.as_view(), name='create'),
    re_path(r'^(?P<brand_id>[0-9]+)/$', views.BrandDetail.as_view(), name='detail'),
]
