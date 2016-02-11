from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UserFormView.as_view(), name='user'),
    url(r'^notes/$', views.OSFUserFormView.as_view(), name='notes')
]
