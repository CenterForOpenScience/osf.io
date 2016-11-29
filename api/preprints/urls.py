from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.PreprintList.as_view(), name=views.PreprintList.view_name),
    url(r'^(?P<preprint_id>\w+)/$', views.PreprintDetail.as_view(), name=views.PreprintDetail.view_name),
]
