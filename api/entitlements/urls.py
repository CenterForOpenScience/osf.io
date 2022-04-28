from django.conf.urls import url

from api.entitlements import views

app_name = 'osf'

urlpatterns = [
    url(r'^login_availability/$', views.LoginAvailability.as_view(), name=views.LoginAvailability.view_name),
]
