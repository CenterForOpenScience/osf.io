from django.conf.urls import url

from api.crossref import views

app_name = 'osf'

urlpatterns = [
    url(r'^email/$', views.ParseCrossRefConfirmation.as_view(), name=views.ParseCrossRefConfirmation.view_name),
]
