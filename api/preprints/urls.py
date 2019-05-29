from django.conf.urls import url

from . import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.PreprintList.as_view(), name=views.PreprintList.view_name),
    url(r'^(?P<preprint_id>\w+)/$', views.PreprintDetail.as_view(), name=views.PreprintDetail.view_name),
    url(r'^(?P<preprint_id>\w+)/citation/$', views.PreprintCitationDetail.as_view(), name=views.PreprintCitationDetail.view_name),
    url(r'^(?P<preprint_id>\w+)/citation/(?P<style_id>[-\w]+)/$', views.PreprintCitationStyleDetail.as_view(), name=views.PreprintCitationStyleDetail.view_name),
    url(r'^(?P<preprint_id>\w+)/contributors/$', views.PreprintContributorsList.as_view(), name=views.PreprintContributorsList.view_name),
    url(r'^(?P<preprint_id>\w+)/contributors/(?P<user_id>\w+)/$', views.PreprintContributorDetail.as_view(), name=views.PreprintContributorDetail.view_name),
    url(r'^(?P<preprint_id>\w+)/files/$', views.PreprintStorageProvidersList.as_view(), name=views.PreprintStorageProvidersList.view_name),
    url(r'^(?P<preprint_id>\w+)/files/osfstorage/$', views.PreprintFilesList.as_view(), name=views.PreprintFilesList.view_name),
    url(r'^(?P<preprint_id>\w+)/identifiers/$', views.PreprintIdentifierList.as_view(), name=views.PreprintIdentifierList.view_name),
    url(r'^(?P<preprint_id>\w+)/relationships/node/$', views.PreprintNodeRelationship.as_view(), name=views.PreprintNodeRelationship.view_name),
    url(r'^(?P<preprint_id>\w+)/review_actions/$', views.PreprintActionList.as_view(), name=views.PreprintActionList.view_name),
    url(r'^(?P<preprint_id>\w+)/requests/$', views.PreprintRequestListCreate.as_view(), name=views.PreprintRequestListCreate.view_name),
]
