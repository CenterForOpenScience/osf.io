from django.urls import re_path

from api.test import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^throttle/', views.test_throttling, name='test-throttling'),
]
