from django.conf.urls import url

from api.licenses import views

urlpatterns = [
    url(r'^$', views.LicenseList.as_view(), name=views.LicenseList.view_name),
    url(r'^(?P<license_id>\w+)/$', views.LicenseDetail.as_view(), name=views.LicenseDetail.view_name),
]
