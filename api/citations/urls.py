from django.conf.urls import url

from api.citations import views

urlpatterns = [
    url(r'^styles/$', views.CitationStyleList.as_view(), name=views.CitationStyleList.view_name),
    url(r'^styles/(?P<citation_id>\w+)/$', views.CitationStyleDetail.as_view(), name=views.CitationStyleDetail.view_name),
]
