from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.PreprintList.as_view(), name=views.PreprintList.view_name),
    url(r'^(?P<node_id>\w+)/$', views.PreprintDetail.as_view(), name=views.PreprintDetail.view_name),
    url(r'^(?P<node_id>\w+)/authors/$', views.PreprintAuthorsList.as_view(), name=views.PreprintAuthorsList.view_name),
]