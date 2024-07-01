from django.urls import re_path

from api.collection_submission_actions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.CollectionSubmissionActionList.as_view(), name=views.CollectionSubmissionActionList.view_name),
    re_path(r'^(?P<action_id>\w+)/$', views.CollectionSubmissionActionDetail.as_view(), name=views.CollectionSubmissionActionDetail.view_name),
]
