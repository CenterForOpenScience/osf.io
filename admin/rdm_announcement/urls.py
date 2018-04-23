from __future__ import absolute_import

from django.conf.urls import url

from admin.rdm_announcement import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    # url(r'^preview/$', views.preview, name='preview'),
    url(r'^send/$', views.SendView.as_view(), name='send'),
    url(r'^settings/$', views.SettingsView.as_view(), name='settings'),
    url(r'^update/$', views.SettingsUpdateView.as_view(), name='update'),
]