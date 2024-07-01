from django.urls import re_path

from api.banners import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^current/$', views.CurrentBanner.as_view(), name=views.CurrentBanner.view_name),
    re_path(r'^(?P<filename>[^/]+)/$', views.BannerMedia.as_view(), name=views.BannerMedia.view_name),
]
