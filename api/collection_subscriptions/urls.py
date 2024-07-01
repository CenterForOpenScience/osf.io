from django.urls import re_path

from api.subscriptions import views

app_name = 'osf'

urlpatterns = [
    re_path(
        r'(?P<subscription_id>\w+)/$',
        views.CollectionProviderSubscriptionDetail.as_view(),
        name=views.CollectionProviderSubscriptionDetail.view_name,
    ),
]
