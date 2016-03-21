# -*- coding: utf-8 -*-
import datetime
import httplib as http

from flask import request

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError

import framework.auth

from framework.auth import cas, campaigns
from framework import forms, status
from framework.flask import redirect  # VOL-aware redirect
from framework.auth import exceptions
from framework.exceptions import HTTPError
from framework.auth import (logout, get_user, DuplicateEmailError)
from framework.auth.decorators import collect_auth, must_be_logged_in
from framework.auth.forms import (
    MergeAccountForm, RegistrationForm, ResendConfirmationForm,
    ResetPasswordForm, ForgotPasswordForm
)

from website import settings
from website import mails
from website import language
from website import security
from website.models import User
from website.util import web_url_for
from website.util.sanitize import strip_html


@collect_auth
def reset_password(auth, **kwargs):
    if auth.logged_in:
        return auth_logout(redirect_url=request.url)
    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(request.form)

    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or '
            'has expired.'}
        raise HTTPError(400, data=error_data)

    if request.method == 'POST' and form.validate():
        # new random verification key, allows CAS to authenticate the user w/o password one time only.
        user_obj.verification_key = security.random_string(20)
        user_obj.set_password(form.password.data)
        user_obj.save()
        status.push_status_message('Password reset', 'success')
        # Redirect to CAS and authenticate the user with a verification key.
        return redirect(cas.get_login_url(
            web_url_for('user_account', _absolute=True),
            auto=True,
            username=user_obj.username,
            verification_key=user_obj.verification_key
        ))

    forms.push_errors_to_status(form.errors)
    return {
        'verification_key': verification_key,
    }


def forgot_password_post():
    """Attempt to send user password reset or return respective error.
    """
    form = ForgotPasswordForm(request.form, prefix='forgot_password')

    if form.validate():
        email = form.email.data
        user_obj = get_user(email=email)
        if user_obj:
            user_obj.verification_key = security.random_string(20)
            user_obj.save()
            reset_link = "http://{0}{1}".format(
                request.host,
                web_url_for(
                    'reset_password',
                    verification_key=user_obj.verification_key
                )
            )
            mails.send_mail(
                to_addr=email,
                mail=mails.FORGOT_PASSWORD,
                reset_link=reset_link
            )
        status.push_status_message(
            ('If there is an OSF account associated with {0}, an email with instructions on how to reset '
             'the OSF password has been sent to {0}. If you do not receive an email and believe you should '
             'have, please contact OSF Support. ').format(email), 'success')

    forms.push_errors_to_status(form.errors)
    return auth_login(forgot_password_form=form)

@collect_auth
def forgot_password_get(auth, *args, **kwargs):
    """Return forgot password page upon.
    """
    if auth.logged_in:
        return redirect(web_url_for('dashboard'))
    return {}

###############################################################################
# Log in
###############################################################################

@collect_auth
def auth_login(auth, **kwargs):
    """If GET request, show login page. If POST, attempt to log user in if
    login form passsed; else send forgot password email.

    """
    campaign = request.args.get('campaign')
    next_url = request.args.get('next')
    must_login_warning = True

    if campaign:
        next_url = campaigns.campaign_url_for(campaign)

    if not next_url:
        next_url = request.args.get('redirect_url')
        must_login_warning = False

    if next_url:
        # Only allow redirects which are relative root or full domain, disallows external redirects.
        if not (next_url[0] == '/' or next_url.startsWith(settings.DOMAIN)):
            raise HTTPError(http.InvalidURL)

    if auth.logged_in:
        if not request.args.get('logout'):
            if next_url:
                return redirect(next_url)
            return redirect(web_url_for('dashboard'))
        # redirect user to CAS for logout, return here w/o authentication
        return auth_logout(redirect_url=request.url)
    if kwargs.get('first', False):
        status.push_status_message('You may now log in', 'info')

    status_message = request.args.get('status', '')
    if status_message == 'expired':
        status.push_status_message('The private link you used is expired.')

    if next_url and must_login_warning:
        status.push_status_message(language.MUST_LOGIN)
    # set login_url to form action, upon successful authentication specifically w/o logout=True,
    # allows for next to be followed or a redirect to the dashboard.
    redirect_url = web_url_for('auth_login', next=next_url, _absolute=True)

    data = {}
    if campaign and campaign in campaigns.CAMPAIGNS:
        if (campaign == 'institution' and settings.ENABLE_INSTITUTIONS) or campaign != 'institution':
            data['campaign'] = campaign
    data['login_url'] = cas.get_login_url(redirect_url, auto=True)
    data['institution_redirect'] = cas.get_institution_target(redirect_url)
    data['redirect_url'] = next_url

    data['sign_up'] = request.args.get('sign_up', False)

    return data, http.OK


def auth_logout(redirect_url=None):
    """Log out and delete cookie.
    """
    redirect_url = redirect_url or request.args.get('redirect_url') or web_url_for('goodbye', _absolute=True)
    logout()
    if 'reauth' in request.args:
        cas_endpoint = cas.get_login_url(redirect_url)
    else:
        cas_endpoint = cas.get_logout_url(redirect_url)
    resp = redirect(cas_endpoint)
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
    return resp


@collect_auth
def confirm_email_get(token, auth=None, **kwargs):
    """View for email confirmation links.
    Authenticates and redirects to user settings page if confirmation is
    successful, otherwise shows an "Expired Link" error.

    methods: GET
    """
    user = User.load(kwargs['uid'])
    is_merge = 'confirm_merge' in request.args
    is_initial_confirmation = not user.date_confirmed

    if user is None:
        raise HTTPError(http.NOT_FOUND)

    if auth and auth.user and (auth.user._id == user._id or auth.user._id == user.merged_by._id):
        if not is_merge:
            # determine if the user registered through a campaign
            campaign = campaigns.campaign_for_user(user)
            if campaign:
                return redirect(
                    campaigns.campaign_url_for(campaign)
                )
            if len(auth.user.emails) == 1 and len(auth.user.email_verifications) == 0:
                status.push_status_message(language.WELCOME_MESSAGE, 'default', jumbotron=True)

            if token in auth.user.email_verifications:
                status.push_status_message(language.CONFIRM_ALTERNATE_EMAIL_ERROR, 'danger')
            # Go to home page
            return redirect(web_url_for('index'))

        status.push_status_message(language.MERGE_COMPLETE, 'success')
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

        # Send out our welcome message
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user
        )

    # Redirect to CAS and authenticate the user with a verification key.
    user.verification_key = security.random_string(20)
    user.save()

    return redirect(cas.get_login_url(
        request.url,
        auto=True,
        username=user.username,
        verification_key=user.verification_key
    ))


def send_confirm_email(user, email):
    """Sends a confirmation email to `user` to a given email.

    :raises: KeyError if user does not have a confirmation token for the given
        email.
    """
    confirmation_url = user.get_confirmation_url(
        email,
        external=True,
        force=True,
    )

    try:
        merge_target = User.find_one(Q('emails', 'eq', email))
    except NoResultsFound:
        merge_target = None

    campaign = campaigns.campaign_for_user(user)
    # Choose the appropriate email template to use
    if merge_target:
        mail_template = mails.CONFIRM_MERGE
    elif campaign:
        mail_template = campaigns.email_template_for_campaign(campaign)
    elif user.is_active:
        mail_template = mails.CONFIRM_EMAIL
    else:
        mail_template = mails.INITIAL_CONFIRM_EMAIL

    mails.send_mail(
        email,
        mail_template,
        'plain',
        user=user,
        confirmation_url=confirmation_url,
        email=email,
        merge_target=merge_target,
    )


def register_user(**kwargs):
    """Register new user account.

    :param-json str email1:
    :param-json str email2:
    :param-json str password:
    :param-json str fullName:
    :param-json str campaign:
    :raises: HTTPError(http.BAD_REQUEST) if validation fails or user already
        exists

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

        user = framework.auth.register_unconfirmed(
            request.json['email1'],
            request.json['password'],
            full_name,
            campaign=campaign,
        )
        framework.auth.signals.user_registered.send(user)
    except (ValidationValueError, DuplicateEmailError):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(
                message_long=language.ALREADY_REGISTERED.format(
                    email=request.json['email1']
                )
            )
        )

    if settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
        send_confirm_email(user, email=user.username)
        message = language.REGISTRATION_SUCCESS.format(email=user.username)
        return {'message': message}
    else:
        return {'message': 'You may now log in.'}


# TODO: Remove me
def auth_register_post():
    if not settings.ALLOW_REGISTRATION:
        status.push_status_message(language.REGISTRATION_UNAVAILABLE)
        return redirect('/')
    form = RegistrationForm(request.form, prefix='register')

    # Process form
    if form.validate():
        try:
            user = framework.auth.register_unconfirmed(
                form.username.data,
                form.password.data,
                form.fullname.data)
            framework.auth.signals.user_registered.send(user)
        except (ValidationValueError, DuplicateEmailError):
            status.push_status_message(
                language.ALREADY_REGISTERED.format(email=form.username.data))
            return auth_login()
        if user:
            if settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
                send_confirm_email(user, email=user.username)
                message = language.REGISTRATION_SUCCESS.format(email=user.username)
                status.push_status_message(message, 'success')
                return auth_login()
            else:
                return redirect('/login/first/')
    else:
        forms.push_errors_to_status(form.errors)
        return auth_login()


def merge_user_get(**kwargs):
    '''Web view for merging an account. Renders the form for confirmation.
    '''
    return forms.utils.jsonify(MergeAccountForm())


def resend_confirmation():
    """View for resending an email confirmation email.
    """
    form = ResendConfirmationForm(request.form)
    if request.method == 'POST':
        if form.validate():
            clean_email = form.email.data
            user = get_user(email=clean_email)
            if not user:
                return {'form': form}
            try:
                send_confirm_email(user, clean_email)
            except KeyError:  # already confirmed, redirect to dashboard
                status_message = 'Email has already been confirmed.'
                type_ = 'warning'
            else:
                status_message = 'Resent email to <em>{0}</em>'.format(clean_email)
                type_ = 'success'
            status.push_status_message(status_message, type_)
        else:
            forms.push_errors_to_status(form.errors)
    # Don't go anywhere
    return {'form': form}


# TODO: shrink me
@must_be_logged_in
def merge_user_post(auth, **kwargs):
    '''View for merging an account. Takes either JSON or form data.

    Request data should include a "merged_username" and "merged_password" properties
    for the account to be merged in.
    '''
    master = auth.user
    if request.json:
        merged_username = request.json.get("merged_username")
        merged_password = request.json.get("merged_password")
    else:
        form = MergeAccountForm(request.form)
        if not form.validate():
            forms.push_errors_to_status(form.errors)
            return merge_user_get(**kwargs)
        master_password = form.user_password.data
        if not master.check_password(master_password):
            status.push_status_message("Could not authenticate. Please check your username and password.")
            return merge_user_get(**kwargs)
        merged_username = form.merged_username.data
        merged_password = form.merged_password.data
    try:
        merged_user = User.find_one(Q("username", "eq", merged_username))
    except NoResultsFound:
        status.push_status_message("Could not find that user. Please check the username and password.")
        return merge_user_get(**kwargs)
    if master and merged_user:
        if merged_user.check_password(merged_password):
            master.merge_user(merged_user)
            master.save()
            if request.form:
                status.push_status_message("Successfully merged {0} with this account".format(merged_username), 'success')
                return redirect("/settings/")
            return {"status": "success"}
        else:
            status.push_status_message("Could not find that user. Please check the username and password.")
            return merge_user_get(**kwargs)
    else:
        raise HTTPError(http.BAD_REQUEST)


# TODO: Is this used?
def auth_registerbeta():
    return redirect('/account')
