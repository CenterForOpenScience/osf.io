from __future__ import absolute_import

from django.conf.urls import url

from admin.management import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.ManagementCommands.as_view(), name='commands'),
    url(r'^waffle_flag', views.WaffleFlag.as_view(), name='waffle_flag')
]
