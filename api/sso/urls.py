from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.SSOView.as_view(), name=views.SSOView.view_name),
    url(r'^sso$', views.SSOView.as_view(), name=views.SSOView.view_name),
]
