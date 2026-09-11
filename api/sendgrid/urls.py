from django.urls import re_path

from api.sendgrid import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^events/$', views.SendGridEventWebhook.as_view(), name=views.SendGridEventWebhook.view_name),
]
