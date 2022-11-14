from django.conf.urls import url

from api.collection_submissions_actions import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<action_id>\w+)/$', views.CollectionSubmissionActionDetail.as_view(), name=views.CollectionSubmissionActionDetail.view_name),
]
