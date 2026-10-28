from django.urls import re_path
from admin.admin_log import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.AdminLogEntryListView.as_view(), name='list'),
]
