# -*- coding: utf-8 -*-
import datetime
import furl
import httplib as http

import markupsafe
from flask import request
import uuid

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError

from framework import forms, status
from framework import auth as framework_auth
from framework.auth import exceptions
from framework.auth import cas, campaigns
from framework.auth import logout as osf_logout
from framework.auth import get_user
from framework.auth.exceptions import DuplicateEmailError, ExpiredTokenError, InvalidTokenError
from framework.auth.core import generate_verification_key
from framework.auth.decorators import collect_auth, must_be_logged_in
from framework.auth.forms import ResendConfirmationForm, ForgotPasswordForm, ResetPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.sessions.utils import remove_sessions_for_user, remove_session
from framework.sessions import get_session
from website import settings, mails, language

from website.util.time import throttle_period_expired
from website.models import User
from website.util import web_url_for
from website.util.sanitize import strip_html


@collect_auth
def reset_password_get(auth, verification_key=None, **kwargs):
    """
    View for user to land on the reset password page.
    HTTp Method: GET

    :raises: HTTPError(http.BAD_REQUEST) if verification_key is invalid
    """

    # If user is already logged in, log user out
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    # Check if request bears a valid verification_key
    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or has expired.'
        }
        raise HTTPError(400, data=error_data)

    return {
        'verification_key': verification_key,
    }


@collect_auth
def reset_password(auth, **kwargs):
    """ Show reset password page.
    """
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)
    verification_key = kwargs['verification_key']

    # Check if request bears a valid verification_key
    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or has expired.'
        }
        raise HTTPError(400, data=error_data)

    return {
        'verification_key': verification_key
    }


@collect_auth
def forgot_password_get(auth, **kwargs):
    """
    View to user to land on forgot password page.
    HTTP Method: GET
    """

    # If user is already logged in, redirect to dashboard page.
    if auth.logged_in:
        return redirect(web_url_for('dashboard'))

    return {}


@collect_auth
def reset_password_post(auth, verification_key=None, **kwargs):
    """
    View for user to submit reset password form.
    HTTP Method: POST
    :raises: HTTPError(http.BAD_REQUEST) if verification_key is invalid
    """

    # If user is already logged in, log user out
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)

    form = ResetPasswordForm(request.form)

    # Check if request bears a valid verification_key
    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or has expired.'
        }
        raise HTTPError(400, data=error_data)

    if form.validate():
        # new random verification key, allows CAS to authenticate the user w/o password, one-time only.
        # this overwrite also invalidates the verification key generated by forgot_password_post
        user_obj.verification_key = generate_verification_key()
        try:
            user_obj.set_password(form.password.data)
            user_obj.save()
        except exceptions.ChangePasswordError as error:
            for message in error.messages:
                status.push_status_message(message, kind='warning', trust=False)
        else:
            status.push_status_message('Password reset', kind='success', trust=False)
            # redirect to CAS and authenticate the user with the one-time verification key.
            return redirect(cas.get_login_url(
                web_url_for('user_account', _absolute=True),
                username=user_obj.username,
                verification_key=user_obj.verification_key
            ))
    else:
        forms.push_errors_to_status(form.errors)
        # Don't go anywhere

    return {
        'verification_key': verification_key
    }, 400


@collect_auth
def forgot_password_post(auth, **kwargs):
    """
    View for user to submit forgot password form.
    HTTP Method: POST
    """

    # If user is already logged in, redirect to dashboard page.
    if auth.logged_in:
        return redirect(web_url_for('dashboard'))

    form = ForgotPasswordForm(request.form, prefix='forgot_password')

    if form.validate():
        email = form.email.data
        status_message = ('If there is an OSF account associated with {0}, an email with instructions on how to '
                          'reset the OSF password has been sent to {0}. If you do not receive an email and believe '
                          'you should have, please contact OSF Support. ').format(email)
        # check if the user exists
        user_obj = get_user(email=email)
        if user_obj:
            # check forgot_password rate limit
            if throttle_period_expired(user_obj.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                # new random verification key, allows OSF to check whether the reset_password request is valid,
                # this verification key is used twice, one for GET reset_password and one for POST reset_password
                # and it will be destroyed when POST reset_password succeeds
                user_obj.verification_key = generate_verification_key()
                user_obj.email_last_sent = datetime.datetime.utcnow()
                user_obj.save()
                reset_link = furl.urljoin(
                    settings.DOMAIN,
                    web_url_for(
                        'reset_password_get',
                        verification_key=user_obj.verification_key
                    )
                )
                mails.send_mail(
                    to_addr=email,
                    mail=mails.FORGOT_PASSWORD,
                    reset_link=reset_link
                )
                status.push_status_message(status_message, kind='success', trust=False)
            else:
                status.push_status_message('You have recently requested to change your password. Please wait a '
                                           'few minutes before trying again.', kind='error', trust=False)
        else:
            status.push_status_message(status_message, kind='success', trust=False)
    else:
        forms.push_errors_to_status(form.errors)
        # Don't go anywhere

    return {}


@collect_auth
def auth_login(auth, **kwargs):
    """
    This view serves as the entry point for OSF login and campaign login.
    HTTP Method: GET

        GET '/login/' without any query parameter:
            redirect to CAS login page with dashboard as target service

        GET '/login/?logout=true
            log user out and redirect to CAS login page with redirect_url or next_url as target service

        GET '/login/?campaign=instituion:
            if user is logged in, redirect to 'dashboard'
            show institution login

        GET '/login/?campaign=prereg:
            if user is logged in, redirect to prereg home page
            else show sign up page and notify user to sign in, set next to prereg home page

        GET '/login/?next=next_url:
            if user is logged in, redirect to next_url
            else redirect to CAS login page with next_url as target service
    """

    campaign = request.args.get('campaign')
    next_url = request.args.get('next')
    log_out = request.args.get('logout')
    must_login_warning = True

    if not campaign and not next_url and not log_out:
        if auth.logged_in:
            return redirect(web_url_for('dashboard'))
        return redirect(cas.get_login_url(web_url_for('dashboard', _absolute=True)))

    if campaign:
        next_url = campaigns.campaign_url_for(campaign)

    if not next_url:
        next_url = request.args.get('redirect_url')
        must_login_warning = False

    if next_url:
        # Only allow redirects which are relative root or full domain, disallows external redirects.
        if not (next_url[0] == '/'
                or next_url.startswith(settings.DOMAIN)
                or next_url.startswith(settings.CAS_SERVER_URL)
                or next_url.startswith(settings.MFR_SERVER_URL)):
            raise HTTPError(http.InvalidURL)

    if auth.logged_in:
        if not log_out:
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        # redirect user to CAS for logout, return here w/o authentication
        return auth_logout(redirect_url=request.url)

    status_message = request.args.get('status', '')
    if status_message == 'expired':
        status.push_status_message('The private link you used is expired.', trust=False)
        status.push_status_message('The private link you used is expired.  Please <a href="/settings/account/">'
                                   'resend email.</a>', trust=False)

    if next_url and must_login_warning:
        status.push_status_message(language.MUST_LOGIN, trust=False)

    # set login_url to form action, upon successful authentication specifically w/o logout=True,
    # allows for next to be followed or a redirect to the dashboard.
    redirect_url = web_url_for('auth_login', next=next_url, _absolute=True)

    data = {}
    if campaign and campaign in campaigns.CAMPAIGNS:
        if (campaign == 'institution' and settings.ENABLE_INSTITUTIONS) or campaign != 'institution':
            data['campaign'] = campaign
    data['login_url'] = cas.get_login_url(redirect_url)
    data['institution_redirect'] = cas.get_institution_target(redirect_url)
    data['redirect_url'] = next_url
    data['sign_up'] = request.args.get('sign_up', False)
    data['existing_user'] = request.args.get('existing_user', None)

    return data, http.OK


def auth_logout(redirect_url=None, **kwargs):
    """
    Log out, delete current session and remove OSF cookie.
    Redirect to CAS logout which clears sessions and cookies for CAS and Shibboleth (if any).
    Final landing page may vary.
    HTTP Method: GET

    :param redirect_url: url to redirect user after CAS logout, default is 'goodbye'
    :return:
    """

    # OSF tells CAS where it wants to be redirected back after successful logout. However, CAS logout flow
    # may not respect this url if user is authenticated through remote IdP such as institution login
    redirect_url = redirect_url or request.args.get('redirect_url') or web_url_for('goodbye', _absolute=True)
    # OSF log out, remove current OSF session
    osf_logout()
    # set redirection to CAS log out (or log in if 'reauth' is present)
    if 'reauth' in request.args:
        cas_endpoint = cas.get_login_url(redirect_url)
    else:
        cas_endpoint = cas.get_logout_url(redirect_url)
    resp = redirect(cas_endpoint)
    # delete OSF cookie
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
        user_merge = User.find_one(Q('emails', 'eq', unconfirmed_email))
    except NoResultsFound:
        user_merge = False
    if user_merge:
        remove_sessions_for_user(user_merge)
    user.email_verifications[token]['confirmed'] = True
    user.save()
    remove_sessions_for_user(user)
    resp = redirect(redirect_url)
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
    return resp


@collect_auth
def external_login_confirm_email_get(auth, uid, token):
    """
    View for email confirmation links when user first login through external identity provider.
    HTTP Method: GET

    :param auth: the auth context
    :param uid: the user's primary key
    :param token: the verification token
    """
    user = User.load(uid)
    if not user:
        raise HTTPError(http.BAD_REQUEST)

    if auth and auth.user and auth.user._id == user._id:
        new = request.args.get('new', None)
        if new:
            status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
        return redirect(web_url_for('index'))

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
    # create a new user
    if external_status == 'CREATE' and email.lower() == user.username.lower():
        user.register(user.username)
        user.date_last_logged_in = datetime.datetime.utcnow()
        user.external_identity[provider][provider_id] = 'VERIFIED'
        user.social[provider.lower()] = provider_id
        user.save()
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user
        )
        service_url = request.url + '?new=true'
    # link a current user
    elif external_status == 'LINK':
        user.date_last_logged_in = datetime.datetime.utcnow()
        user.external_identity[provider][provider_id] = 'VERIFIED'
        user.social[provider.lower()] = provider_id
        user.save()
        mails.send_mail(
            user=user,
            to_addr=user.username,
            mail=mails.EXTERNAL_LOGIN_LINK_SUCCESS,
            external_id_provider=provider,
        )
        service_url = request.url

    del user.email_verifications[token]
    user.save()

    # redirect to CAS and authenticate the user with the verification key
    user.verification_key = generate_verification_key()
    user.save()
    return redirect(cas.get_login_url(
        service_url,
        username=user.username,
        verification_key=user.verification_key
    ))


@collect_auth
def confirm_email_get(token, auth=None, **kwargs):
    """
    View for email confirmation links. Authenticates and redirects to user settings page if confirmation is successful,
    otherwise shows an "Expired Link" error.
    HTTP Method: GET
    """

    user = User.load(kwargs['uid'])
    is_merge = 'confirm_merge' in request.args
    is_initial_confirmation = not user.date_confirmed
    log_out = request.args.get('logout', None)

    if user is None:
        raise HTTPError(http.NOT_FOUND)

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
            if len(auth.user.emails) == 1 and len(auth.user.email_verifications) == 0:
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
        user.date_last_login = datetime.datetime.utcnow()
        user.save()

        # send out our welcome message
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user
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


def send_confirm_email(user, email, external_id_provider=None, external_id=None):
    """
    Sends a confirmation email to `user` to a given email.

    :raises: KeyError if user does not have a confirmation token for the given email.
    """

    confirmation_url = user.get_confirmation_url(
        email,
        external=True,
        force=True,
        external_id_provider=external_id_provider
    )

    try:
        merge_target = User.find_one(Q('emails', 'eq', email))
    except NoResultsFound:
        merge_target = None
    campaign = campaigns.campaign_for_user(user)

    # Choose the appropriate email template to use and add existing_user flag if a merge or adding an email.
    if external_id_provider and external_id:  # first time login through external identity provider
        if user.external_identity[external_id_provider][external_id] == 'CREATE':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_CREATE
        elif user.external_identity[external_id_provider][external_id] == 'LINK':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK
    elif merge_target:  # merge account
        mail_template = mails.CONFIRM_MERGE
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif user.is_active:  # add email
        mail_template = mails.CONFIRM_EMAIL
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif campaign:  # campaign
        # TODO: In the future, we may want to make confirmation email configurable as well (send new user to
        #   appropriate landing page or with redirect after)
        mail_template = campaigns.email_template_for_campaign(campaign)
    else:  # account creation
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
    )


@collect_auth
def auth_register(auth, **kwargs):
    """
    View for sign-up page.
    HTTP Method: GET
    """

    # If user is already logged in, redirect to dashboard page.
    if auth.logged_in:
        return redirect(web_url_for('dashboard'))

    return {}, http.OK


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

    # Verify email address match
    json_data = request.get_json()
    if str(json_data['email1']).lower() != str(json_data['email2']).lower():
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Email addresses must match.')
        )
    try:
        full_name = request.json['fullName']
        full_name = strip_html(full_name)

        campaign = json_data.get('campaign')
        if campaign and campaign not in campaigns.CAMPAIGNS:
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
        status_message = ('If there is an OSF account associated with this unconfirmed email {0}, '
                          'a confirmation email has been resent to it. If you do not receive an email and believe '
                          'you should have, please contact OSF Support.').format(clean_email)
        kind = 'success'
        if user:
            if throttle_period_expired(user.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                try:
                    send_confirm_email(user, clean_email)
                except KeyError:
                    # already confirmed, redirect to dashboard
                    status_message = 'This email {0} has already been confirmed.'.format(clean_email)
                    kind = 'warning'
                user.email_last_sent = datetime.datetime.utcnow()
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

    if form.validate():
        clean_email = form.email.data
        user = get_user(email=clean_email)
        external_identity = {
            external_id_provider: {
                external_id: None,
            },
        }
        if user:
            external_status = ''
            # 0. check if this user is already linked with other profile
            if user.external_identity:
                if external_id_provider in user.external_identity:
                    if user.external_identity[external_id_provider]:
                        if external_id in user.external_identity[external_id_provider]:
                            external_status = user.external_identity[external_id_provider][external_id]

            if external_status == 'CREATE' or external_status == 'LINK':
                # TODO: [#OSF-6933] handle pending status: the current or another user also claimed this osf account but not confirmed
                pass

            # 1. update user oauth, with pending status
            external_identity[external_id_provider][external_id] = 'LINK'
            if external_id_provider in user.external_identity:
                user.external_identity[external_id_provider].update(external_identity[external_id_provider])
            else:
                user.external_identity.update(external_identity)
            # 2. add unconfirmed email and send confirmation email
            user.add_unconfirmed_email(clean_email, external_identity=external_identity)
            user.save()
            send_confirm_email(user, user.username, external_id_provider=external_id_provider, external_id=external_id)
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
            user = User.create_unconfirmed(
                username=clean_email,
                password=str(uuid.uuid4()),
                fullname=fullname,
                external_identity=external_identity,
                campaign=None
            )
            # TODO: [#OSF-6934] update social fields, verified social fields cannot be modified
            user.save()
            # 3. send confirmation email
            send_confirm_email(user, user.username, external_id_provider=external_id_provider, external_id=external_id)
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
