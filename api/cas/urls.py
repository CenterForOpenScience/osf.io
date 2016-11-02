from django.conf.urls import url

from api.cas import views

urlpatterns = [
    url(r'^login/$', views.CasLogin.as_view(), name=views.CasLogin.view_name),
    url(r'^register/$', views.CasRegister.as_view(), name=views.CasRegister.view_name),
]
