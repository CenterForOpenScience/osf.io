# -*- coding: utf-8 -*-
import datetime
import furl
import httplib as http

import markupsafe
from flask import request
import uuid

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationError
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
from framework.auth.utils import ensure_external_identity_uniqueness, validate_recaptcha
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
    user_obj = User.load(uid)
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
    user_obj = User.load(uid)
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
            else:
                # TODO [OSF-6673]: Use the feature in [OSF-6998] for user to resend claim email.
                # if the user account is not claimed yet
                if (user_obj.is_invited and
                        user_obj.unclaimed_records and
                        not user_obj.date_last_login and
                        not user_obj.is_claimed and
                        not user_obj.is_registered):
                    status_message = 'You cannot reset password on this account. Please contact OSF Support.'
                    kind = 'error'
                else:
                    # new random verification key (v2)
                    user_obj.verification_key_v2 = generate_verification_key(verification_type='password')
                    user_obj.email_last_sent = datetime.datetime.utcnow()
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
        must_login_warning = False
        next_url = campaigns.campaign_url_for(campaign)

    if not next_url:
        next_url = request.args.get('redirect_url')
        must_login_warning = False

    if not validate_next_url(next_url):
        raise HTTPError(http.BAD_REQUEST)

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

    When users click the confirm link, they are expected not to be logged in. If not, they will be logged out first and
    redirected back to this view. After OSF verifies the link and performs all actions, they will be automatically
    logged in through CAS and redirected back to this view again being authenticated.

    :param auth: the auth context
    :param uid: the user's primary key
    :param token: the verification token
    """
    user = User.load(uid)
    if not user:
        raise HTTPError(http.BAD_REQUEST)

    # if user is already logged in
    if auth and auth.user:
        # if it is the expected user
        if auth.user._id == user._id:
            new = request.args.get('new', None)
            if new:
                status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
            return redirect(web_url_for('index'))
        # if it is a wrong user
        return auth_logout(redirect_url=request.url)

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
        user.set_password(uuid.uuid4(), notify=False)
        user.register(email)

    if email.lower() not in user.emails:
        user.emails.append(email.lower())

    user.date_last_logged_in = datetime.datetime.utcnow()
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
            user=user
        )
        service_url = service_url + '?new=true'
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


def send_confirm_email(user, email, renew=False, external_id_provider=None, external_id=None):
    """
    Sends `user` a confirmation to the given `email`.


    :param user: the user
    :param email: the email
    :param renew: refresh the token
    :param external_id_provider: user's external id provider
    :param external_id: user's external id
    :return:
    :raises: KeyError if user does not have a confirmation token for the given email.
    """

    confirmation_url = user.get_confirmation_url(
        email,
        external=True,
        force=True,
        renew=renew,
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

    # Verify that email address match
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
        status_message = ('If there is an OSF account associated with this unconfirmed email {0}, '
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
            send_confirm_email(user, clean_email, external_id_provider=external_id_provider, external_id=external_id)
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


def validate_next_url(next_url):
    """
    Non-view helper function that checks `next_url`.
    Only allow redirects which are relative root or full domain (CAS, OSF and MFR).
    Disallows external redirects.

    :param next_url: the next url to check
    :return: True if valid, False otherwise
    """

    if next_url:
        # disable external domain using `//`: the browser allows `//` as a shortcut for non-protocol specific requests
        # like http:// or https:// depending on the use of SSL on the page already.
        if next_url.startswith('//'):
            return False
        # only OSF, MFR and CAS domains are allowed
        if not (next_url[0] == '/' or
                next_url.startswith(settings.DOMAIN) or
                next_url.startswith(settings.CAS_SERVER_URL) or
                next_url.startswith(settings.MFR_SERVER_URL)):
            return False
    return True
