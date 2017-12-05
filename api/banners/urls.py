from django.conf.urls import url

from api.banners import views

app_name = 'osf'

urlpatterns = [
    url(r'^current/$', views.CurrentBanner.as_view(), name=views.CurrentBanner.view_name),
]
