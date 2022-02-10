from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.SearchView.as_view(), name='search'),
    url(r'^result/$', views.ResultView.as_view(), name='result'),
    url(r'^settings/$', views.SettingsView.as_view(), name='settings'),
]
