from django.conf.urls import url

from api.cas import views

urlpatterns = [
    url(r'^login/$', views.CasLogin.as_view(), name=views.CasLogin.view_name),
]