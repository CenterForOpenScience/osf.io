from django.urls import re_path

from api.collection_submissions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<collection_submission_id>[a-zA-Z0-9._-]+)/actions/$', views.CollectionSubmissionActionsList.as_view(), name=views.CollectionSubmissionActionsList.view_name),
]
