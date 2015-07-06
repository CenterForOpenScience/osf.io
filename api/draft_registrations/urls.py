from django.conf.urls import url
from api.draft_registrations import views

urlpatterns = [
    url(r'^$', views.DraftRegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<registration_id>\w+)/$', views.DraftRegistrationDetail.as_view(), name='registration-detail')
]
