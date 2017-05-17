from django.conf.urls import url

from api.cas import views

urlpatterns = [
    # auth
    url(r'^auth/login/$', views.AuthLogin.as_view(), name=views.AuthLogin.view_name),
    url(r'^auth/register/$', views.AuthRegister.as_view(), name=views.AuthRegister.view_name),
    url(r'^auth/institution/', views.AuthInstitution.as_view(), name=views.AuthInstitution.view_name),
    url(r'^auth/verifyEmail/', views.AuthVerifyEmail.as_view(), name=views.AuthVerifyEmail.view_name),
    url(r'^auth/resetPassword/', views.AuthResetPassword.as_view(), name=views.AuthResetPassword.view_name),
    # service
    url(r'^service/findAccount/', views.UtilityFindAccount.as_view(), name=views.UtilityFindAccount.view_name),
    url(r'^service/checkPAT/$', views.UtilityCheckPersonalAccessToken.as_view(), name=views.UtilityCheckPersonalAccessToken.view_name),
    url(r'^service/checkOauthScope/$', views.UtilityCheckOauthScope.as_view(), name=views.UtilityCheckOauthScope.view_name),
    url(r'^service/loadInstitutions/$', views.ServiceLoadInstitutions.as_view(), name=views.ServiceLoadInstitutions.view_name),
    url(r'^service/loadDeveloperApps/$', views.ServiceLoadDeveloperApps.as_view(), name=views.ServiceLoadDeveloperApps.view_name),
]
