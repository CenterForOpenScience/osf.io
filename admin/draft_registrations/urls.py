from django.urls import re_path

from admin.draft_registrations import views


app_name = 'draft_registrations'


urlpatterns = [
    re_path(r'^$', views.UserDraftRegistrationSearchView.as_view(), name='search'),
    re_path(r'^(?P<draft_registration_id>\w+)/$', views.DraftRegistrationView.as_view(), name='detail'),
]
