from django.conf.urls import re_path

from api.collection_submissions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<collection_submission_id>\w+)-(?P<collection_id>\w+)/$', views.CollectionSubmissionDetail.as_view(), name=views.CollectionSubmissionDetail.view_name),
]
