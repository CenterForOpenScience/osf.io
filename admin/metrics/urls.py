from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.OSFStatisticsListView.as_view(), name='stats_list'),
    url(r'^update/$', views.update_metrics, name='update'),
]
