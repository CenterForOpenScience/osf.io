from django.conf.urls import url

from api.collection_submission_actions import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.CollectionSubmissionActionList.as_view(), name=views.CollectionSubmissionActionList.view_name),
    url(r'^(?P<action_id>\w+)/$', views.CollectionSubmissionActionDetail.as_view(), name=views.CollectionSubmissionActionDetail.view_name),
]
