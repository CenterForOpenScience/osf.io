from django.conf.urls import url
# from views import ConfDetailView, ConfFormView, ConfListView
# from django.views.decorators.http import require_POST

from . import views

urlpatterns = [
    url(r'^$', views.create_conference, name='create_conference'),
    url(r'^conference_list/$', views.ConferenceList.as_view(), name='conference_list'),
    # url(
    #     r'^(?P<conference_endpoint>[a-z0-9]+)/$',
    #     views.ConferenceDetail.as_view(),
    #     name='conference_detail'
    # ),
]
