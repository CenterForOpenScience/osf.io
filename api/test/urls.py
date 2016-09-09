from django.conf.urls import url

from api.test import views

urlpatterns = [
    url(r'^throttle/', views.test_throttling, name='test-throttling'),
]
