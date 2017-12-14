from django.conf.urls import url
from api.wb import views

app_name = 'osf'

urlpatterns = [
    url(r'^move/', views.MoveFile.as_view(), name=views.MoveFile.view_name),
    url(r'^copy/', views.MoveFile.as_view(), name=views.MoveFile.view_name),
]
