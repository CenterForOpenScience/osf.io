from django.conf.urls import url

from api.cas import views

urlpatterns = [
    # auth
    url(r'^auth/login/$', views.AuthLogin.as_view(), name=views.AuthLogin.view_name),
    url(r'^auth/register/$', views.AuthRegister.as_view(), name=views.AuthRegister.view_name),
    url(r'^auth/institution/$', views.AuthInstitution.as_view(), name=views.AuthInstitution.view_name),
    url(r'^auth/external/$', views.AuthExternal.as_view(), name=views.AuthExternal.view_name),
    url(r'^auth/external/createOrLink/$', views.AuthExternalCreateOrLinkOsfAccount.as_view(), name=views.AuthExternalCreateOrLinkOsfAccount.view_name),
    url(r'^auth/verifyEmail/$', views.AuthVerifyEmail.as_view(), name=views.AuthVerifyEmail.view_name),
    url(r'^auth/resetPassword/$', views.AuthResetPassword.as_view(), name=views.AuthResetPassword.view_name),
    # service
    url(r'^service/findAccount/$', views.ServiceFindAccount.as_view(), name=views.ServiceFindAccount.view_name),
    url(r'^service/checkPAT/$', views.ServiceCheckPersonalAccessToken.as_view(), name=views.ServiceCheckPersonalAccessToken.view_name),
    url(r'^service/checkOauthScope/$', views.ServiceCheckOauthScope.as_view(), name=views.ServiceCheckOauthScope.view_name),
    url(r'^service/loadInstitutions/$', views.ServiceLoadInstitutions.as_view(), name=views.ServiceLoadInstitutions.view_name),
    url(r'^service/loadDeveloperApps/$', views.ServiceLoadDeveloperApps.as_view(), name=views.ServiceLoadDeveloperApps.view_name),
]
