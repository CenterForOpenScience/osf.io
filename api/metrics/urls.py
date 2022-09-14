from django.conf.urls import re_path

from . import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^raw/(?P<url_path>[a-z0-9._/]*)$', views.RawMetricsView.as_view(), name=views.RawMetricsView.view_name),
    re_path(r'^preprints/views/$', views.PreprintViewMetrics.as_view(), name=views.PreprintViewMetrics.view_name),
    re_path(r'^preprints/downloads/$', views.PreprintDownloadMetrics.as_view(), name=views.PreprintDownloadMetrics.view_name),
    re_path(r'^registries_moderation/transitions/$', views.RegistriesModerationMetricsView.as_view(), name=views.RegistriesModerationMetricsView.view_name),
]
