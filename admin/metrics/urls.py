from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.MetricsView.as_view(), name='metrics'),
]
