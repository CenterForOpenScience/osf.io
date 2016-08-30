from django.conf.urls import url

from api.citations import views

urlpatterns = [
    url(r'^$', views.CitationList.as_view(), name=views.CitationList.view_name),
    url(r'^(?P<citation_id>\w+)/$', views.CitationDetail.as_view(), name=views.CitationDetail.view_name),
]
