from django.urls import re_path

from api.tokens import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.TokenList.as_view(), name='token-list'),
    re_path(r'^(?P<_id>\w+)/$', views.TokenDetail.as_view(), name='token-detail'),
    re_path(r'^(?P<_id>\w+)/scopes/$', views.TokenScopesList.as_view(), name='token-scopes-list'),
]
