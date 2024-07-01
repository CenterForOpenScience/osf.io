from django.urls import re_path
from admin.banners import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.BannerList.as_view(), name='list'),
    re_path(r'^create/$', views.CreateBanner.as_view(), name='create'),
    re_path(r'^(?P<banner_id>[0-9]+)/$', views.BannerDetail.as_view(), name='detail'),
    re_path(r'^(?P<banner_id>[0-9]+)/delete/$', views.DeleteBanner.as_view(), name='delete'),
]
