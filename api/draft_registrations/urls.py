from django.urls import re_path

from api.draft_registrations import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.DraftRegistrationList.as_view(), name=views.DraftRegistrationList.view_name),
    re_path(r'^(?P<draft_id>\w+)/$', views.DraftRegistrationDetail.as_view(), name=views.DraftRegistrationDetail.view_name),
    re_path(r'^(?P<draft_id>\w+)/contributors/$', views.DraftContributorsList.as_view(), name=views.DraftContributorsList.view_name),
    re_path(r'^(?P<draft_id>\w+)/contributors/(?P<user_id>\w+)/$', views.DraftContributorDetail.as_view(), name=views.DraftContributorDetail.view_name),
    re_path(r'^(?P<draft_id>\w+)/bibliographic_contributors/$', views.DraftBibliographicContributorsList.as_view(), name=views.DraftBibliographicContributorsList.view_name),
    re_path(r'^(?P<draft_id>\w+)/institutions/$', views.DraftInstitutionsList.as_view(), name=views.DraftInstitutionsList.view_name),
    re_path(r'^(?P<draft_id>\w+)/relationships/institutions/$', views.DraftInstitutionsRelationship.as_view(), name=views.DraftInstitutionsRelationship.view_name),
    re_path(r'^(?P<draft_id>\w+)/relationships/subjects/$', views.DraftSubjectsRelationship.as_view(), name=views.DraftSubjectsRelationship.view_name),
    re_path(r'^(?P<draft_id>\w+)/subjects/$', views.DraftSubjectsList.as_view(), name=views.DraftSubjectsList.view_name),
]
