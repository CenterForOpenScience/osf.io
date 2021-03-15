from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.BrandList.as_view(), name='list'),
    url(r'^create/$', views.BrandCreate.as_view(), name='create'),
    url(r'^(?P<brand_id>[0-9]+)/$', views.BrandDetail.as_view(), name='detail'),
]
