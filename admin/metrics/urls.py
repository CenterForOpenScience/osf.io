from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.OSFStatisticsListView.as_view(), name='stats_list'),
]
