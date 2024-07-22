from django.urls import re_path

from api.citations import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^styles/$', views.CitationStyleList.as_view(), name=views.CitationStyleList.view_name),
    re_path(r'^styles/(?P<citation_id>\w+)/$', views.CitationStyleDetail.as_view(), name=views.CitationStyleDetail.view_name),
]
