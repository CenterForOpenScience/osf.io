from django.conf.urls import url

from api.collection_submissions.views import CollectionSubmissionDetail
from api.collection_submissions_actions.views import CollectionSubmissionActionList

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<collection_submission_id>\w+\-\w+)/$', CollectionSubmissionDetail.as_view(), name=CollectionSubmissionDetail.view_name),
    url(r'^(?P<collection_submission_id>\w+\-\w+)/actions/$', CollectionSubmissionActionList.as_view(), name=CollectionSubmissionActionList.view_name),
]
