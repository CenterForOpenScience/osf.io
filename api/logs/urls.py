from django.conf.urls import url

from api.logs import views

urlpatterns = [
    url(r'^$', views.LogList.as_view(), name='log-list'),
]
