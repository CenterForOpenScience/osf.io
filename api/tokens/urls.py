from __future__ import unicode_literals
from django.conf.urls import url

from api.tokens import views

urlpatterns = [
    url(r'^$', views.TokenList.as_view(), name='token-list'),
    url(r'^(?P<_id>\w+)/$', views.TokenDetail.as_view(), name='token-detail')
]
