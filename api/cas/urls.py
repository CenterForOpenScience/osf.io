from django.conf.urls import url

from api.cas import views

urlpatterns = [
    # login
    url(r'^login/osf/$', views.LoginOSF.as_view(), name=views.LoginOSF.view_name),
    url(r'^login/institution/$', views.LoginInstitution.as_view(), name=views.LoginInstitution.view_name),
    url(r'^login/external/$', views.LoginExternal.as_view(), name=views.LoginExternal.view_name),
    # account
    url(r'^account/register/osf/$', views.AccountRegisterOSF.as_view(), name=views.AccountRegisterOSF.view_name),
    url(r'^account/register/external/', views.AccountRegisterExternal.as_view(), name=views.AccountRegisterExternal.view_name),
    url(r'^account/verify/osf/$', views.AccountVerifyOSF.as_view(), name=views.AccountVerifyOSF.view_name),
    url(r'^account/verify/osf/resend/$', views.AccountVerifyOSFResend.as_view(), name=views.AccountVerifyOSFResend.view_name),
    url(r'^account/verify/external/$', views.AccountVerifyExternal.as_view(), name=views.AccountVerifyExternal.view_name),
    url(r'^account/password/forgot/$', views.AccountPasswordForgot.as_view(), name=views.AccountPasswordForgot.view_name),
    url(r'^account/password/reset/$', views.AccountPasswordReset.as_view(), name=views.AccountPasswordReset.view_name),
    # service
    url(r'^service/oauth/token/$', views.ServiceOauthToken.as_view(), name=views.ServiceOauthToken.view_name),
    url(r'^service/oauth/scope/$', views.ServiceOauthScope.as_view(), name=views.ServiceOauthScope.view_name),
    url(r'^service/oauth/apps/$', views.ServiceOauthApps.as_view(), name=views.ServiceOauthApps.view_name),
    url(r'^service/institutions/$', views.ServiceInstitutions.as_view(), name=views.ServiceInstitutions.view_name),
]
