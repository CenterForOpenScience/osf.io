from django.urls import re_path

from admin.draft_registrations import views


app_name = 'draft_registrations'


urlpatterns = [
    re_path(r'^$', views.UserDraftRegistrationSearchView.as_view(), name='search'),
]
