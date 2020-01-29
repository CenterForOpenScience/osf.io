from django.conf.urls import url

from api.draft_registrations import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<draft_id>\w+)/$', views.DraftRegistrationDetail.as_view(), name=views.DraftRegistrationDetail.view_name),
]
