from django.conf.urls import url

from api.cas import views

urlpatterns = [
    url(r'^auth/login/$', views.CasLogin.as_view(), name=views.CasLogin.view_name),
    url(r'^auth/register/$', views.CasRegister.as_view(), name=views.CasRegister.view_name),
    url(r'^auth/institution/', views.CasInstitutionAuthenticate.as_view(), name=views.CasInstitutionAuthenticate.view_name),
    url(r'^service/personalAccessToken/$', views.CasPersonalAccessToken.as_view(), name=views.CasPersonalAccessToken.view_name),
    url(r'^service/oauthScopes/$', views.CasOAuthScopes.as_view(), name=views.CasOAuthScopes.view_name),
    url(r'^service/institutions/$', views.CasInstitutions.as_view(), name=views.CasInstitutions.view_name),
    url(r'^service/developerApps/$', views.CasDeveloperApplications.as_view(), name=views.CasDeveloperApplications.view_name),
]
