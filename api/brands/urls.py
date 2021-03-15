from django.conf.urls import url

from api.brands import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.BrandList.as_view(), name=views.BrandList.view_name),
    url(r'^(?P<brand_id>\w+)/$', views.BrandDetail.as_view(), name=views.BrandDetail.view_name),
]
