from __future__ import absolute_import

from django.conf.urls import re_path

from admin.subjects import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.SubjectListView.as_view(), name='list'),
    re_path(r'^(?P<pk>[0-9]+)/$', views.SubjectUpdateView.as_view(),
        name='update'),
]
