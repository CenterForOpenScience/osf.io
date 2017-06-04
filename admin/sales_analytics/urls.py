from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^dashboard$', views.DashboardView.as_view(), name='dashboard'),
]
