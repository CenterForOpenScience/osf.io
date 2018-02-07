from django.conf.urls import url

from api.test import views

app_name = 'osf'

urlpatterns = [
    url(r'^throttle/', views.test_throttling, name='test-throttling'),
]
