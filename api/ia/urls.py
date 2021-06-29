from django.conf.urls import url
from api.ia import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<target_id>\w+)/done/', views.IACallbackView.as_view(), name=views.IACallbackView.view_name),
]
