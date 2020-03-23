from django.conf.urls import url

from . import views

app_name = 'osf'

urlpatterns = [
    url(r'^preprints/views/$', views.PreprintViewMetrics.as_view(), name=views.PreprintViewMetrics.view_name),
    url(r'^preprints/downloads/$', views.PreprintDownloadMetrics.as_view(), name=views.PreprintDownloadMetrics.view_name),
]
