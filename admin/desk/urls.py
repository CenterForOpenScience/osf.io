from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.DeskCaseList.as_view(), name='cases'),
    url(r'^cases/id-(?P<user_id>[a-z0-9]+)/$', views.DeskCaseList.as_view(),
        name='user_cases'),
]
