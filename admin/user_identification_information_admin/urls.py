from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.UserIdentificationListAdminView.as_view(), name='index'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserIdentificationDetailsAdminView.as_view(), name='details'),

]
