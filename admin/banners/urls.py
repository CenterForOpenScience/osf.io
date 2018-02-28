from django.conf.urls import url
from admin.banners import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.BannerList.as_view(), name='list'),
    url(r'^create/$', views.CreateBanner.as_view(), name='create'),
    url(r'^(?P<banner_id>[0-9]+)/$', views.BannerDetail.as_view(), name='detail'),
    url(r'^(?P<banner_id>[0-9]+)/delete/$', views.DeleteBanner.as_view(), name='delete'),
]
