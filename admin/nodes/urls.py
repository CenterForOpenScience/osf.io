from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.NodeFormView.as_view(), name='node'),
]
