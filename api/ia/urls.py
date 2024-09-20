from django.urls import re_path
from api.ia import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<target_id>\w+)/done/', views.IACallbackView.as_view(), name=views.IACallbackView.view_name),
]
