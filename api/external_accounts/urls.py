from django.conf.urls import url
from . import views

ROUTE_BASE = r'^(?P<external_account_id>\w+)/'

urlpatterns = [
    url(ROUTE_BASE + '$', views.ExternalAccountDetail.as_view(), name='external-account-detail'),
]
