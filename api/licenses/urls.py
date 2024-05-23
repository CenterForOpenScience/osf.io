from django.urls import re_path

from api.licenses import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.LicenseList.as_view(), name=views.LicenseList.view_name),
    re_path(r'^(?P<license_id>\w+)/$', views.LicenseDetail.as_view(), name=views.LicenseDetail.view_name),
]
