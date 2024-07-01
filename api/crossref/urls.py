from django.urls import re_path

from api.crossref import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^email/$', views.ParseCrossRefConfirmation.as_view(), name=views.ParseCrossRefConfirmation.view_name),
]
