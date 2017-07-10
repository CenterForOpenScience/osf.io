from __future__ import absolute_import

from django.conf.urls import url

from admin.subjects import views

urlpatterns = [
    url(r'^$', views.SubjectListView.as_view(), name='list'),
    url(r'^(?P<pk>[0-9]+)/$', views.SubjectUpdateView.as_view(),
        name='update'),
]
