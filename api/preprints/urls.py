from django.urls import re_path

from . import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.PreprintList.as_view(), name=views.PreprintList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/$', views.PreprintDetail.as_view(), name=views.PreprintDetail.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/bibliographic_contributors/$', views.PreprintBibliographicContributorsList.as_view(), name=views.PreprintBibliographicContributorsList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/citation/$', views.PreprintCitationDetail.as_view(), name=views.PreprintCitationDetail.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/citation/(?P<style_id>[-\w]+)/$', views.PreprintCitationStyleDetail.as_view(), name=views.PreprintCitationStyleDetail.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/contributors/$', views.PreprintContributorsList.as_view(), name=views.PreprintContributorsList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/contributors/(?P<user_id>[-\w]+)/$', views.PreprintContributorDetail.as_view(), name=views.PreprintContributorDetail.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/files/$', views.PreprintStorageProvidersList.as_view(), name=views.PreprintStorageProvidersList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/files/osfstorage/$', views.PreprintFilesList.as_view(), name=views.PreprintFilesList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/identifiers/$', views.PreprintIdentifierList.as_view(), name=views.PreprintIdentifierList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/relationships/node/$', views.PreprintNodeRelationship.as_view(), name=views.PreprintNodeRelationship.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/relationships/subjects/$', views.PreprintSubjectsRelationship.as_view(), name=views.PreprintSubjectsRelationship.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/review_actions/$', views.PreprintActionList.as_view(), name=views.PreprintActionList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/requests/$', views.PreprintRequestListCreate.as_view(), name=views.PreprintRequestListCreate.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/subjects/$', views.PreprintSubjectsList.as_view(), name=views.PreprintSubjectsList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/institutions/$', views.PreprintInstitutionsList.as_view(), name=views.PreprintInstitutionsList.view_name),
    re_path(r'^(?P<preprint_id>[A-Za-z0-9_]+)/relationships/institutions/$', views.PreprintInstitutionsRelationship.as_view(), name=views.PreprintInstitutionsRelationship.view_name),
]
