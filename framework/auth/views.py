# -*- coding: utf-8 -*-
import furl
import httplib as http
import urllib

import markupsafe
from django.core.exceptions import ValidationError
from django.utils import timezone
from flask import request

from framework import forms, sentry, status
from framework import auth as framework_auth
from framework.auth import exceptions
from framework.auth import cas, campaigns
from framework.auth import logout as osf_logout
from framework.auth import get_user
from framework.auth.exceptions import DuplicateEmailError, ExpiredTokenError, InvalidTokenError
from framework.auth.core import generate_verification_key
from framework.auth.decorators import block_bing_preview, collect_auth, must_be_logged_in
from framework.auth.forms import ResendConfirmationForm, ForgotPasswordForm, ResetPasswordForm
from framework.auth.utils import ensure_external_identity_uniqueness, validate_recaptcha
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.sessions.utils import remove_sessions_for_user, remove_session
from framework.sessions import get_session
from framework.utils import throttle_period_expired
from osf.models import OSFUser
from osf.utils.sanitize import strip_html
from website import settings, mails, language
from website.util import web_url_for
from osf.exceptions import ValidationValueError
from osf.models.provider import PreprintProvider
from osf.utils.requests import check_select_for_update

@block_bing_preview
@collect_auth
def reset_password_get(auth, uid=None, token=None):
    """
    View for user to land on the reset password page.
    HTTp Method: GET

    :param auth: the authentication state
    :param uid: the user id
    :param token: the token in verification key
    :return
    :raises: HTTPError(http.BAD_REQUEST) if verification key for the user is invalid, has expired or was used
    """

    # if users are logged in, log them out and redirect back to this page
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    # Check if request bears a valid pair of `uid` and `token`
    user_obj = OSFUser.load(uid)
    if not (user_obj and user_obj.verify_password_token(token=token)):
        error_data = {
            'message_short': 'Invalid Request.',
            'message_long': 'The requested URL is invalid, has expired, or was already used',
        }
        raise HTTPError(http.BAD_REQUEST, data=error_data)

    # refresh the verification key (v2)
    user_obj.verification_key_v2 = generate_verification_key(verification_type='password')
    user_obj.save()

    return {
        'uid': user_obj._id,
        'token': user_obj.verification_key_v2['token'],
    }


def reset_password_post(uid=None, token=None):
    """
    View for user to submit reset password form.
    HTTP Method: POST

    :param uid: the user id
    :param token: the token in verification key
    :return:
    :raises: HTTPError(http.BAD_REQUEST) if verification key for the user is invalid, has expired or was used
    """

    form = ResetPasswordForm(request.form)

    # Check if request bears a valid pair of `uid` and `token`
    user_obj = OSFUser.load(uid)
    if not (user_obj and user_obj.verify_password_token(token=token)):
        error_data = {
            'message_short': 'Invalid Request.',
            'message_long': 'The requested URL is invalid, has expired, or was already used',
        }
        raise HTTPError(http.BAD_REQUEST, data=error_data)

    if not form.validate():
        # Don't go anywhere
        forms.push_errors_to_status(form.errors)
    else:
        # clear verification key (v2)
        user_obj.verification_key_v2 = {}
        # new verification key (v1) for CAS
        user_obj.verification_key = generate_verification_key(verification_type=None)
        try:
            user_obj.set_password(form.password.data)
            user_obj.save()
        except exceptions.ChangePasswordError as error:
            for message in error.messages:
                status.push_status_message(message, kind='warning', trust=False)
        else:
            status.push_status_message('Password reset', kind='success', trust=False)
            # redirect to CAS and authenticate the user automatically with one-time verification key.
            return redirect(cas.get_login_url(
                web_url_for('user_account', _absolute=True),
                username=user_obj.username,
                verification_key=user_obj.verification_key
            ))

    return {
        'uid': user_obj._id,
        'token': user_obj.verification_key_v2['token'],
    }


@collect_auth
def forgot_password_get(auth):
    """
    View for user to land on the forgot password page.
    HTTP Method: GET

    :param auth: the authentication context
    :return
    """

    # if users are logged in, log them out and redirect back to this page
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    return {}


def forgot_password_post():
    """
    View for user to submit forgot password form.
    HTTP Method: POST
    :return {}
    """

    form = ForgotPasswordForm(request.form, prefix='forgot_password')

    if not form.validate():
        # Don't go anywhere
        forms.push_errors_to_status(form.errors)
    else:
        email = form.email.data
        status_message = ('If there is an OSF account associated with {0}, an email with instructions on how to '
                          'reset the OSF password has been sent to {0}. If you do not receive an email and believe '
                          'you should have, please contact OSF Support. ').format(email)
        kind = 'success'
        # check if the user exists
        user_obj = get_user(email=email)
        if user_obj:
            # rate limit forgot_password_post
            if not throttle_period_expired(user_obj.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                status_message = 'You have recently requested to change your password. Please wait a few minutes ' \
                                 'before trying again.'
                kind = 'error'
            # TODO [OSF-6673]: Use the feature in [OSF-6998] for user to resend claim email.
            elif user_obj.is_active:
                # new random verification key (v2)
                user_obj.verification_key_v2 = generate_verification_key(verification_type='password')
                user_obj.email_last_sent = timezone.now()
                user_obj.save()
                reset_link = furl.urljoin(
                    settings.DOMAIN,
                    web_url_for(
                        'reset_password_get',
                        uid=user_obj._id,
                        token=user_obj.verification_key_v2['token']
                    )
                )
                mails.send_mail(
                    to_addr=email,
                    mail=mails.FORGOT_PASSWORD,
                    reset_link=reset_link
                )

        status.push_status_message(status_message, kind=kind, trust=False)

    return {}


def login_and_register_handler(auth, login=True, campaign=None, next_url=None, logout=None):
    """
    Non-view helper to handle `login` and `register` requests.

    :param auth: the auth context
    :param login: `True` if `GET /login`, `False` if `GET /register`
    :param campaign: a target campaign defined in `auth.campaigns`
    :param next_url: the service url for CAS login or redirect url for OSF
    :param logout: used only for `claim_user_registered`
    :return: data object that contains actions for `auth_register` and `auth_login`
    :raises: http.BAD_REQUEST
    """

    # Only allow redirects which are relative root or full domain. Disallows external redirects.
    if next_url and not validate_next_url(next_url):
        raise HTTPError(http.BAD_REQUEST)

    data = {
        'status_code': http.FOUND if login else http.OK,
        'next_url': next_url,
        'campaign': None,
        'must_login_warning': False,
    }

    # login or register with campaign parameter
    if campaign:
        if validate_campaign(campaign):
            # GET `/register` or '/login` with `campaign=institution`
            # unlike other campaigns, institution login serves as an alternative for authentication
            if campaign == 'institution':
                if next_url is None:
                    next_url = web_url_for('dashboard', _absolute=True)
                data['status_code'] = http.FOUND
                if auth.logged_in:
                    data['next_url'] = next_url
                else:
                    data['next_url'] = cas.get_login_url(next_url, campaign='institution')
            # for non-institution campaigns
            else:
                destination = next_url if next_url else campaigns.campaign_url_for(campaign)
                if auth.logged_in:
                    # if user is already logged in, go to the campaign landing page
                    data['status_code'] = http.FOUND
                    data['next_url'] = destination
                else:
                    # if user is logged out, go to the osf register page with campaign context
                    if login:
                        # `GET /login?campaign=...`
                        data['next_url'] = web_url_for('auth_register', campaign=campaign, next=destination)
                    else:
                        # `GET /register?campaign=...`
                        data['campaign'] = campaign
                        if campaigns.is_proxy_login(campaign):
                            data['next_url'] = web_url_for(
                                'auth_login',
                                next=destination,
                                _absolute=True
                            )
                        else:
                            data['next_url'] = destination
        else:
            # invalid campaign, inform sentry and redirect to non-campaign sign up or sign in
            redirect_view = 'auth_login' if login else 'auth_register'
            data['status_code'] = http.FOUND
            data['next_url'] = web_url_for(redirect_view, campaigns=None, next=next_url)
            data['campaign'] = None
            sentry.log_message(
                '{} is not a valid campaign. Please add it if this is a new one'.format(campaign)
            )
    # login or register with next parameter
    elif next_url:
        if logout:
            # handle `claim_user_registered`
            data['next_url'] = next_url
            if auth.logged_in:
                # log user out and come back
                data['status_code'] = 'auth_logout'
            else:
                # after logout, land on the register page with "must_login" warning
                data['status_code'] = http.OK
                data['must_login_warning'] = True
        elif auth.logged_in:
            # if user is already logged in, redirect to `next_url`
            data['status_code'] = http.FOUND
            data['next_url'] = next_url
        elif login:
            # `/login?next=next_url`: go to CAS login page with current request url as service url
            data['status_code'] = http.FOUND
            data['next_url'] = cas.get_login_url(request.url)
        else:
            # `/register?next=next_url`: land on OSF register page with request url as next url
            data['status_code'] = http.OK
            data['next_url'] = request.url
    else:
        # `/login/` or `/register/` without any parameter
        if auth.logged_in:
            data['status_code'] = http.FOUND
        data['next_url'] = web_url_for('dashboard', _absolute=True)

    return data


@collect_auth
def auth_login(auth):
    """
    View (no template) for OSF Login.
    Redirect user based on `data` returned from `login_and_register_handler`.

    `/login` only takes valid campaign, valid next, or no query parameter
    `login_and_register_handler()` handles the following cases:
        if campaign and logged in, go to campaign landing page (or valid next_url if presents)
        if campaign and logged out, go to campaign register page (with next_url if presents)
        if next_url and logged in, go to next url
        if next_url and logged out, go to cas login page with current request url as service parameter
        if none, go to `/dashboard` which is decorated by `@must_be_logged_in`

    :param auth: the auth context
    :return: redirects
    """

    campaign = request.args.get('campaign')
    next_url = request.args.get('next')

    data = login_and_register_handler(auth, login=True, campaign=campaign, next_url=next_url)
    if data['status_code'] == http.FOUND:
        return redirect(data['next_url'])


@collect_auth
def auth_register(auth):
    """
    View for OSF register. Land on the register page, redirect or go to `auth_logout`
    depending on `data` returned by `login_and_register_handler`.

    `/register` only takes a valid campaign, a valid next, the logout flag or no query parameter
    `login_and_register_handler()` handles the following cases:
        if campaign and logged in, go to campaign landing page (or valid next_url if presents)
        if campaign and logged out, go to campaign register page (with next_url if presents)
        if next_url and logged in, go to next url
        if next_url and logged out, go to cas login page with current request url as service parameter
        if next_url and logout flag, log user out first and then go to the next_url
        if none, go to `/dashboard` which is decorated by `@must_be_logged_in`

    :param auth: the auth context
    :return: land, redirect or `auth_logout`
    :raise: http.BAD_REQUEST
    """

    context = {}
    # a target campaign in `auth.campaigns`
    campaign = request.args.get('campaign')
    # the service url for CAS login or redirect url for OSF
    next_url = request.args.get('next')
    # used only for `claim_user_registered`
    logout = request.args.get('logout')

    # logout must have next_url
    if logout and not next_url:
        raise HTTPError(http.BAD_REQUEST)

    data = login_and_register_handler(auth, login=False, campaign=campaign, next_url=next_url, logout=logout)

    # land on register page
    if data['status_code'] == http.OK:
        if data['must_login_warning']:
            status.push_status_message(language.MUST_LOGIN, trust=False)
        destination = cas.get_login_url(data['next_url'])
        # "Already have and account?" link
        context['non_institution_login_url'] = destination
        # "Sign In" button in navigation bar, overwrite the default value set in routes.py
        context['login_url'] = destination
        # "Login through your institution" link
        context['institution_login_url'] = cas.get_login_url(data['next_url'], campaign='institution')
        context['preprint_campaigns'] = {k._id + '-preprints': {
            'id': k._id,
            'name': k.name,
            'logo_path': settings.PREPRINTS_ASSETS + k._id + '/square_color_no_transparent.png'
        } for k in PreprintProvider.objects.all() if k._id != 'osf'}
        context['campaign'] = data['campaign']
        return context, http.OK
    # redirect to url
    elif data['status_code'] == http.FOUND:
        return redirect(data['next_url'])
    # go to other views
    elif data['status_code'] == 'auth_logout':
        return auth_logout(redirect_url=data['next_url'])

    raise HTTPError(http.BAD_REQUEST)

@collect_auth
def auth_logout(auth, redirect_url=None, next_url=None):
    """
    Log out, delete current session and remove OSF cookie.
    If next url is valid and auth is logged in, redirect to CAS logout endpoint with the current request url as service.
    If next url is valid and auth is logged out, redirect directly to the next url.
    Otherwise, redirect to CAS logout or login endpoint with redirect url as service.
    The CAS logout endpoint which clears sessions and cookies for CAS and Shibboleth.
    HTTP Method: GET

    Note 1: OSF tells CAS where it wants to be redirected back after successful logout. However, CAS logout flow may not
    respect this url if user is authenticated through remote identity provider.
    Note 2: The name of the query parameter is `next`, `next_url` is used to avoid python reserved word.

    :param auth: the authentication context
    :param redirect_url: url to DIRECTLY redirect after CAS logout, default is `OSF/goodbye`
    :param next_url: url to redirect after OSF logout, which is after CAS logout
    :return: the response
    """

    # For `?next=`:
    #   takes priority
    #   the url must be a valid OSF next url,
    #   the full request url is set to CAS service url,
    #   does not support `reauth`
    # For `?redirect_url=`:
    #   the url must be valid CAS service url
    #   the redirect url is set to CAS service url.
    #   support `reauth`

    # logout/?next=<an OSF verified next url>
    next_url = next_url or request.args.get('next', None)
    if next_url and validate_next_url(next_url):
        cas_logout_endpoint = cas.get_logout_url(request.url)
        if auth.logged_in:
            resp = redirect(cas_logout_endpoint)
        else:
            resp = redirect(next_url)
    # logout/ or logout/?redirect_url=<a CAS verified redirect url>
    else:
        redirect_url = redirect_url or request.args.get('redirect_url') or web_url_for('goodbye', _absolute=True)
        # set redirection to CAS log out (or log in if `reauth` is present)
        if 'reauth' in request.args:
            cas_endpoint = cas.get_login_url(redirect_url)
        else:
            cas_endpoint = cas.get_logout_url(redirect_url)
        resp = redirect(cas_endpoint)

    # perform OSF logout
    osf_logout()

    # set response to delete OSF cookie
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)

    return resp


def auth_email_logout(token, user):
    """
    When a user is adding an email or merging an account, add the email to the user and log them out.
    """

    redirect_url = cas.get_logout_url(service_url=cas.get_login_url(service_url=web_url_for('index', _absolute=True)))
    try:
        unconfirmed_email = user.get_unconfirmed_email_for_token(token)
    except InvalidTokenError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Bad token',
            'message_long': 'The provided token is invalid.'
        })
    except ExpiredTokenError:
        status.push_status_message('The private link you used is expired.')
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Expired link',
            'message_long': 'The private link you used is expired.'
        })
    try:
        user_merge = OSFUser.objects.get(emails__address=unconfirmed_email)
    except OSFUser.DoesNotExist:
        user_merge = False
    if user_merge:
        remove_sessions_for_user(user_merge)
    user.email_verifications[token]['confirmed'] = True
    user.save()
    remove_sessions_for_user(user)
    resp = redirect(redirect_url)
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
    return resp


@block_bing_preview
@collect_auth
def external_login_confirm_email_get(auth, uid, token):
    """
    View for email confirmation links when user first login through external identity provider.
    HTTP Method: GET

    When users click the confirm link, they are expected not to be logged in. If not, they will be logged out first and
    redirected back to this view. After OSF verifies the link and performs all actions, they will be automatically
    logged in through CAS and redirected back to this view again being authenticated.

    :param auth: the auth context
    :param uid: the user's primary key
    :param token: the verification token
    """

    user = OSFUser.load(uid)
    if not user:
        raise HTTPError(http.BAD_REQUEST)

    destination = request.args.get('destination')
    if not destination:
        raise HTTPError(http.BAD_REQUEST)

    # if user is already logged in
    if auth and auth.user:
        # if it is a wrong user
        if auth.user._id != user._id:
            return auth_logout(redirect_url=request.url)
        # if it is the expected user
        new = request.args.get('new', None)
        if destination in campaigns.get_campaigns():
            # external domain takes priority
            campaign_url = campaigns.external_campaign_url_for(destination)
            if not campaign_url:
                campaign_url = campaigns.campaign_url_for(destination)
            return redirect(campaign_url)
        if new:
            status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
        return redirect(web_url_for('dashboard'))

    # token is invalid
    if token not in user.email_verifications:
        raise HTTPError(http.BAD_REQUEST)
    verification = user.email_verifications[token]
    email = verification['email']
    provider = verification['external_identity'].keys()[0]
    provider_id = verification['external_identity'][provider].keys()[0]
    # wrong provider
    if provider not in user.external_identity:
        raise HTTPError(http.BAD_REQUEST)
    external_status = user.external_identity[provider][provider_id]

    try:
        ensure_external_identity_uniqueness(provider, provider_id, user)
    except ValidationError as e:
        raise HTTPError(http.FORBIDDEN, e.message)

    if not user.is_registered:
        user.register(email)

    if not user.emails.filter(address=email.lower()):
        user.emails.create(address=email.lower())

    user.date_last_logged_in = timezone.now()
    user.external_identity[provider][provider_id] = 'VERIFIED'
    user.social[provider.lower()] = provider_id
    del user.email_verifications[token]
    user.verification_key = generate_verification_key()
    user.save()

    service_url = request.url

    if external_status == 'CREATE':
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )
        service_url += '&{}'.format(urllib.urlencode({'new': 'true'}))
    elif external_status == 'LINK':
        mails.send_mail(
            user=user,
            to_addr=user.username,
            mail=mails.EXTERNAL_LOGIN_LINK_SUCCESS,
            external_id_provider=provider,
        )

    # redirect to CAS and authenticate the user with the verification key
    return redirect(cas.get_login_url(
        service_url,
        username=user.username,
        verification_key=user.verification_key
    ))


@block_bing_preview
@collect_auth
def confirm_email_get(token, auth=None, **kwargs):
    """
    View for email confirmation links. Authenticates and redirects to user settings page if confirmation is successful,
    otherwise shows an "Expired Link" error.
    HTTP Method: GET
    """

    is_merge = 'confirm_merge' in request.args

    try:
        if not is_merge or not check_select_for_update():
            user = OSFUser.objects.get(guids___id=kwargs['uid'])
        else:
            user = OSFUser.objects.filter(guids___id=kwargs['uid']).select_for_update().get()
    except OSFUser.DoesNotExist:
        raise HTTPError(http.NOT_FOUND)

    is_initial_confirmation = not user.date_confirmed
    log_out = request.args.get('logout', None)

    # if the user is merging or adding an email (they already are an osf user)
    if log_out:
        return auth_email_logout(token, user)

    if auth and auth.user and (auth.user._id == user._id or auth.user._id == user.merged_by._id):
        if not is_merge:
            # determine if the user registered through a campaign
            campaign = campaigns.campaign_for_user(user)
            if campaign:
                return redirect(campaigns.campaign_url_for(campaign))

            # go to home page with push notification
            if auth.user.emails.count() == 1 and len(auth.user.email_verifications) == 0:
                status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
            if token in auth.user.email_verifications:
                status.push_status_message(language.CONFIRM_ALTERNATE_EMAIL_ERROR, kind='danger', trust=True)
            return redirect(web_url_for('index'))

        status.push_status_message(language.MERGE_COMPLETE, kind='success', trust=False)
        return redirect(web_url_for('user_account'))

    try:
        user.confirm_email(token, merge=is_merge)
    except exceptions.EmailConfirmTokenError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })

    if is_initial_confirmation:
        user.update_date_last_login()
        user.save()

        # send out our welcome message
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

    # new random verification key, allows CAS to authenticate the user w/o password one-time only.
    user.verification_key = generate_verification_key()
    user.save()
    # redirect to CAS and authenticate the user with a verification key.
    return redirect(cas.get_login_url(
        request.url,
        username=user.username,
        verification_key=user.verification_key
    ))


@must_be_logged_in
def unconfirmed_email_remove(auth=None):
    """
    Called at login if user cancels their merge or email add.
    HTTP Method: DELETE
    """

    user = auth.user
    json_body = request.get_json()
    try:
        given_token = json_body['token']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Missing token',
            'message_long': 'Must provide a token'
        })
    user.clean_email_verifications(given_token=given_token)
    user.save()
    return {
        'status': 'success',
        'removed_email': json_body['address']
    }, 200


@must_be_logged_in
def unconfirmed_email_add(auth=None):
    """
    Called at login if user confirms their merge or email add.
    HTTP Method: PUT
    """
    user = auth.user
    json_body = request.get_json()
    try:
        token = json_body['token']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Missing token',
            'message_long': 'Must provide a token'
        })
    try:
        user.confirm_email(token, merge=True)
    except exceptions.InvalidTokenError:
        raise InvalidTokenError(http.BAD_REQUEST, data={
            'message_short': 'Invalid user token',
            'message_long': 'The user token is invalid'
        })
    except exceptions.EmailConfirmTokenError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })

    user.save()
    return {
        'status': 'success',
        'removed_email': json_body['address']
    }, 200


def send_confirm_email(user, email, renew=False, external_id_provider=None, external_id=None, destination=None):
    """
    Sends `user` a confirmation to the given `email`.


    :param user: the user
    :param email: the email
    :param renew: refresh the token
    :param external_id_provider: user's external id provider
    :param external_id: user's external id
    :param destination: the destination page to redirect after confirmation
    :return:
    :raises: KeyError if user does not have a confirmation token for the given email.
    """

    confirmation_url = user.get_confirmation_url(
        email,
        external=True,
        force=True,
        renew=renew,
        external_id_provider=external_id_provider,
        destination=destination
    )

    try:
        merge_target = OSFUser.objects.get(emails__address=email)
    except OSFUser.DoesNotExist:
        merge_target = None

    campaign = campaigns.campaign_for_user(user)
    branded_preprints_provider = None

    # Choose the appropriate email template to use and add existing_user flag if a merge or adding an email.
    if external_id_provider and external_id:
        # First time login through external identity provider, link or create an OSF account confirmation
        if user.external_identity[external_id_provider][external_id] == 'CREATE':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_CREATE
        elif user.external_identity[external_id_provider][external_id] == 'LINK':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK
    elif merge_target:
        # Merge account confirmation
        mail_template = mails.CONFIRM_MERGE
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif user.is_active:
        # Add email confirmation
        mail_template = mails.CONFIRM_EMAIL
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif campaign:
        # Account creation confirmation: from campaign
        mail_template = campaigns.email_template_for_campaign(campaign)
        if campaigns.is_proxy_login(campaign) and campaigns.get_service_provider(campaign) != 'OSF':
            branded_preprints_provider = campaigns.get_service_provider(campaign)
    else:
        # Account creation confirmation: from OSF
        mail_template = mails.INITIAL_CONFIRM_EMAIL

    mails.send_mail(
        email,
        mail_template,
        'plain',
        user=user,
        confirmation_url=confirmation_url,
        email=email,
        merge_target=merge_target,
        external_id_provider=external_id_provider,
        branded_preprints_provider=branded_preprints_provider,
        osf_support_email=settings.OSF_SUPPORT_EMAIL
    )


def register_user(**kwargs):
    """
    Register new user account.
    HTTP Method: POST

    :param-json str email1:
    :param-json str email2:
    :param-json str password:
    :param-json str fullName:
    :param-json str campaign:

    :raises: HTTPError(http.BAD_REQUEST) if validation fails or user already exists
    """

    # Verify that email address match.
    # Note: Both `landing.mako` and `register.mako` already have this check on the form. Users can not submit the form
    # if emails do not match. However, this check should not be removed given we may use the raw api call directly.
    json_data = request.get_json()
    if str(json_data['email1']).lower() != str(json_data['email2']).lower():
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Email addresses must match.')
        )

    # Verify that captcha is valid
    if settings.RECAPTCHA_SITE_KEY and not validate_recaptcha(json_data.get('g-recaptcha-response'), remote_ip=request.remote_addr):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Invalid Captcha')
        )

    try:
        full_name = request.json['fullName']
        full_name = strip_html(full_name)

        campaign = json_data.get('campaign')
        if campaign and campaign not in campaigns.get_campaigns():
            campaign = None

        user = framework_auth.register_unconfirmed(
            request.json['email1'],
            request.json['password'],
            full_name,
            campaign=campaign,
        )
        framework_auth.signals.user_registered.send(user)
    except (ValidationValueError, DuplicateEmailError):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(
                message_long=language.ALREADY_REGISTERED.format(
                    email=markupsafe.escape(request.json['email1'])
                )
            )
        )
    except ValidationError as e:
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long=e.message)
        )

    if settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
        send_confirm_email(user, email=user.username)
        message = language.REGISTRATION_SUCCESS.format(email=user.username)
        return {'message': message}
    else:
        return {'message': 'You may now log in.'}


@collect_auth
def resend_confirmation_get(auth):
    """
    View for user to land on resend confirmation page.
    HTTP Method: GET
    """

    # If user is already logged in, log user out
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    form = ResendConfirmationForm(request.form)
    return {
        'form': form,
    }


@collect_auth
def resend_confirmation_post(auth):
    """
    View for user to submit resend confirmation form.
    HTTP Method: POST
    """

    # If user is already logged in, log user out
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    form = ResendConfirmationForm(request.form)

    if form.validate():
        clean_email = form.email.data
        user = get_user(email=clean_email)
        status_message = ('If there is an OSF account associated with this unconfirmed email address {0}, '
                          'a confirmation email has been resent to it. If you do not receive an email and believe '
                          'you should have, please contact OSF Support.').format(clean_email)
        kind = 'success'
        if user:
            if throttle_period_expired(user.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                try:
                    send_confirm_email(user, clean_email, renew=True)
                except KeyError:
                    # already confirmed, redirect to dashboard
                    status_message = 'This email {0} has already been confirmed.'.format(clean_email)
                    kind = 'warning'
                user.email_last_sent = timezone.now()
                user.save()
            else:
                status_message = ('You have recently requested to resend your confirmation email. '
                                 'Please wait a few minutes before trying again.')
                kind = 'error'
        status.push_status_message(status_message, kind=kind, trust=False)
    else:
        forms.push_errors_to_status(form.errors)

    # Don't go anywhere
    return {'form': form}


def external_login_email_get():
    """
    Landing view for first-time oauth-login user to enter their email address.
    HTTP Method: GET
    """

    form = ResendConfirmationForm(request.form)
    session = get_session()
    if not session.is_external_first_login:
        raise HTTPError(http.UNAUTHORIZED)

    external_id_provider = session.data['auth_user_external_id_provider']

    return {
        'form': form,
        'external_id_provider': external_id_provider
    }


def external_login_email_post():
    """
    View to handle email submission for first-time oauth-login user.
    HTTP Method: POST
    """

    form = ResendConfirmationForm(request.form)
    session = get_session()
    if not session.is_external_first_login:
        raise HTTPError(http.UNAUTHORIZED)

    external_id_provider = session.data['auth_user_external_id_provider']
    external_id = session.data['auth_user_external_id']
    fullname = session.data['auth_user_fullname']
    service_url = session.data['service_url']

    # TODO: @cslzchen use user tags instead of destination
    destination = 'dashboard'
    for campaign in campaigns.get_campaigns():
        if campaign != 'institution':
            # Handle different url encoding schemes between `furl` and `urlparse/urllib`.
            # OSF use `furl` to parse service url during service validation with CAS. However, `web_url_for()` uses
            # `urlparse/urllib` to generate service url. `furl` handles `urlparser/urllib` generated urls while ` but
            # not vice versa.
            campaign_url = furl.furl(campaigns.campaign_url_for(campaign)).url
            external_campaign_url = furl.furl(campaigns.external_campaign_url_for(campaign)).url
            if campaigns.is_proxy_login(campaign):
                # proxy campaigns: OSF Preprints and branded ones
                if check_service_url_with_proxy_campaign(str(service_url), campaign_url, external_campaign_url):
                    destination = campaign
                    # continue to check branded preprints even service url matches osf preprints
                    if campaign != 'osf-preprints':
                        break
            elif service_url.startswith(campaign_url):
                # osf campaigns: OSF Prereg and ERPC
                destination = campaign
                break

    if form.validate():
        clean_email = form.email.data
        user = get_user(email=clean_email)
        external_identity = {
            external_id_provider: {
                external_id: None,
            },
        }
        try:
            ensure_external_identity_uniqueness(external_id_provider, external_id, user)
        except ValidationError as e:
            raise HTTPError(http.FORBIDDEN, e.message)
        if user:
            # 1. update user oauth, with pending status
            external_identity[external_id_provider][external_id] = 'LINK'
            if external_id_provider in user.external_identity:
                user.external_identity[external_id_provider].update(external_identity[external_id_provider])
            else:
                user.external_identity.update(external_identity)
            # 2. add unconfirmed email and send confirmation email
            user.add_unconfirmed_email(clean_email, external_identity=external_identity)
            user.save()
            send_confirm_email(
                user,
                clean_email,
                external_id_provider=external_id_provider,
                external_id=external_id,
                destination=destination
            )
            # 3. notify user
            message = language.EXTERNAL_LOGIN_EMAIL_LINK_SUCCESS.format(
                external_id_provider=external_id_provider,
                email=user.username
            )
            kind = 'success'
            # 4. remove session and osf cookie
            remove_session(session)
        else:
            # 1. create unconfirmed user with pending status
            external_identity[external_id_provider][external_id] = 'CREATE'
            user = OSFUser.create_unconfirmed(
                username=clean_email,
                password=None,
                fullname=fullname,
                external_identity=external_identity,
                campaign=None
            )
            # TODO: [#OSF-6934] update social fields, verified social fields cannot be modified
            user.save()
            # 3. send confirmation email
            send_confirm_email(
                user,
                user.username,
                external_id_provider=external_id_provider,
                external_id=external_id,
                destination=destination
            )
            # 4. notify user
            message = language.EXTERNAL_LOGIN_EMAIL_CREATE_SUCCESS.format(
                external_id_provider=external_id_provider,
                email=user.username
            )
            kind = 'success'
            # 5. remove session
            remove_session(session)
        status.push_status_message(message, kind=kind, trust=False)
    else:
        forms.push_errors_to_status(form.errors)

    # Don't go anywhere
    return {
        'form': form,
        'external_id_provider': external_id_provider
    }


def validate_campaign(campaign):
    """
    Non-view helper function that validates `campaign`.

    :param campaign: the campaign to validate
    :return: True if valid, False otherwise
    """

    return campaign and campaign in campaigns.get_campaigns()


def validate_next_url(next_url):
    """
    Non-view helper function that checks `next_url`.
    Only allow redirects which are relative root or full domain (CAS, OSF and MFR).
    Disallows external redirects.

    :param next_url: the next url to check
    :return: True if valid, False otherwise
    """

    # disable external domain using `//`: the browser allows `//` as a shortcut for non-protocol specific requests
    # like http:// or https:// depending on the use of SSL on the page already.
    if next_url.startswith('//'):
        return False

    # only OSF, MFR, CAS and Branded Preprints domains are allowed
    if next_url[0] == '/' or next_url.startswith(settings.DOMAIN):
        # OSF
        return True
    if next_url.startswith(settings.CAS_SERVER_URL) or next_url.startswith(settings.MFR_SERVER_URL):
        # CAS or MFR
        return True
    for url in campaigns.get_external_domains():
        # Branded Preprints Phase 2
        if next_url.startswith(url):
            return True

    return False


def check_service_url_with_proxy_campaign(service_url, campaign_url, external_campaign_url=None):
    """
    Check if service url belongs to proxy campaigns: OSF Preprints and branded ones.
    Both service_url and campaign_url are parsed using `furl` encoding scheme.

    :param service_url: the `furl` formatted service url
    :param campaign_url: the `furl` formatted campaign url
    :param external_campaign_url: the `furl` formatted external campaign url
    :return: the matched object or None
    """

    prefix_1 = settings.DOMAIN + 'login/?next=' + campaign_url
    prefix_2 = settings.DOMAIN + 'login?next=' + campaign_url

    valid = service_url.startswith(prefix_1) or service_url.startswith(prefix_2)
    valid_external = False

    if external_campaign_url:
        prefix_3 = settings.DOMAIN + 'login/?next=' + external_campaign_url
        prefix_4 = settings.DOMAIN + 'login?next=' + external_campaign_url
        valid_external = service_url.startswith(prefix_3) or service_url.startswith(prefix_4)

    return valid or valid_external
