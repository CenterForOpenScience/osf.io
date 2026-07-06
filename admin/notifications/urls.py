from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'$', views.NotificationsList.as_view(), name='list'),
    re_path(r'types/$', views.NotificationTypeList.as_view(), name='types_list'),
    re_path(r'type_display/(?P<pk>\d+)/$', views.NotificationTypeDisplay.as_view(), name='type_display'),
    re_path(r'type_detail/(?P<pk>\d+)/$', views.NotificationTypeDetail.as_view(), name='type_detail'),
    re_path(r'types_preview/(?P<pk>\d+)/$', views.NotificationTypePreview.as_view(), name='types_preview'),
    re_path(r'subscriptions/$', views.NotificationSubscriptionsList.as_view(), name='subscriptions_list'),
    re_path(r'email_tasks/$', views.EmailTasksList.as_view(), name='email_tasks_list'),
]
