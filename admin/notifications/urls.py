from django.urls import re_path
from admin.notifications import views

app_name = 'notifications'

urlpatterns = [
    re_path(r'^$', views.handle_duplicate_notifications, name='handle_duplicate_notifications'),
]
