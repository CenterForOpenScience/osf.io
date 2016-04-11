from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.create_conference, name='create_conference'),
    url(r'^conference_list/$', views.ConferenceList.as_view(), name='conference_list'),
    url(r'^update_conference/(?P<endpoint>[A-Za-z0-9]+)$', views.conference_update_view,
        name='conference_update_view'),
]
