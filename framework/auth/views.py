# -*- coding: utf-8 -*-
import datetime
import httplib as http

from flask import request

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError

import framework.auth
from framework import forms, status
from framework.flask import redirect  # VOL-aware redirect
from framework.auth import exceptions
from framework.exceptions import HTTPError
from framework.sessions import set_previous_url
from framework.auth import (login, logout, get_user, DuplicateEmailError)
from framework.auth.decorators import collect_auth, must_be_logged_in
from framework.auth.forms import (
    ForgotPasswordForm,
    MergeAccountForm,
    RegistrationForm,
    ResendConfirmationForm,
    ResetPasswordForm,
    SignInForm,
)

import website.settings
from website import mails
from website import language
from website import security
from website.models import User
from website.util import web_url_for


def reset_password(**kwargs):

    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(request.form)

    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or '
                            'has expired.',
        }
        raise HTTPError(400, data=error_data)

    if request.method == 'POST' and form.validate():
        user_obj.verification_key = None
        user_obj.set_password(form.password.data)
        user_obj.save()
        status.push_status_message('Password reset')
        return redirect('/account/')

    forms.push_errors_to_status(form.errors)
    return {
        'verification_key': verification_key,
    }


# TODO: Rewrite async
def forgot_password():
    form = ForgotPasswordForm(request.form, prefix='forgot_password')

    if form.validate():
        email = form.email.data
        user_obj = get_user(username=email)
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
            status.push_status_message('Reset email sent to {0}'.format(email))
        else:
            status.push_status_message(
                'Email {email} not found'.format(email=email)
            )

    forms.push_errors_to_status(form.errors)
    return auth_login(forgot_password_form=form)


###############################################################################
# Log in
###############################################################################

# TODO: Rewrite async
@collect_auth
def auth_login(auth,
               registration_form=None,
               forgot_password_form=None,
               **kwargs):
    """If GET request, show login page. If POST, attempt to log user in if
    login form passsed; else send forgot password email.

    """
    if auth.logged_in:
        if not request.args.get('logout'):
            return redirect('/dashboard/')
        logout()
    direct_call = registration_form or forgot_password_form
    if request.method == 'POST' and not direct_call:
        form = SignInForm(request.form)
        if form.validate():
            twofactor_code = None
            if 'twofactor' in website.settings.ADDONS_REQUESTED:
                twofactor_code = form.two_factor.data
            try:
                response = login(
                    form.username.data,
                    form.password.data,
                    twofactor_code
                )
                return response
            except exceptions.LoginDisabledError:
                status.push_status_message(language.DISABLED, 'error')
            except exceptions.LoginNotAllowedError:
                status.push_status_message(
                    message=language.UNCONFIRMED,
                    kind='warning',
                    safe=True,
                )
                # Don't go anywhere
                return {'next': ''}
            except exceptions.PasswordIncorrectError:
                status.push_status_message(language.LOGIN_FAILED)
            except exceptions.TwoFactorValidationError:
                status.push_status_message(language.TWO_FACTOR_FAILED)
        forms.push_errors_to_status(form.errors)

    if kwargs.get('first', False):
        status.push_status_message('You may now log in')

    # Get next URL from GET / POST data
    next_url = request.args.get(
        'next',
        request.form.get(
            'next_url',
            ''
        )
    )
    status_message = request.args.get('status', '')
    if status_message == 'expired':
        status.push_status_message('The private link you used is expired.')

    code = http.OK
    if next_url:
        status.push_status_message(language.MUST_LOGIN)
        # Don't raise error if user is being logged out
        if not request.args.get('logout'):
            code = http.UNAUTHORIZED
    return {'next': next_url}, code


def auth_logout():
    """Log out and delete cookie.
    """
    logout()
    rv = redirect('/goodbye/')
    rv.delete_cookie(website.settings.COOKIE_NAME)
    return rv


def confirm_email_get(**kwargs):
    """View for email confirmation links.
    Authenticates and redirects to user settings page if confirmation is
    successful, otherwise shows an "Expired Link" error.

    methods: GET
    """
    user = User.load(kwargs['uid'])
    token = kwargs['token']
    if user:
        if user.confirm_email(token):  # Confirm and register the user
            user.date_last_login = datetime.datetime.utcnow()
            user.save()

            # Go to settings page
            status.push_status_message(
                message=language.WELCOME_MESSAGE,
                kind='success',
                safe=True,
            )
            response = redirect('/settings/')

            return framework.auth.authenticate(user, response=response)
    # Return data for the error template
    return {
        'code': http.BAD_REQUEST,
        'message_short': 'Link Expired',
        'message_long': language.LINK_EXPIRED
    }, http.BAD_REQUEST


def send_confirm_email(user, email):
    """Sends a confirmation email to `user` to a given email.

    :raises: KeyError if user does not have a confirmation token for the given
        email.
    """
    confirmation_url = user.get_confirmation_url(email, external=True)
    mails.send_mail(email, mails.CONFIRM_EMAIL, 'plain',
                    user=user,
                    confirmation_url=confirmation_url)


def register_user(**kwargs):
    """Register new user account.

    :param-json str email1:
    :param-json str email2:
    :param-json str password:
    :param-json str fullName:
    :raises: HTTPError(http.BAD_REQUEST) if validation fails or user already
        exists

    """
    # Verify email address match
    if request.json['email1'] != request.json['email2']:
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Email addresses must match.')
        )
    # TODO: Sanitize fields
    try:
        user = framework.auth.register_unconfirmed(
            request.json['email1'],
            request.json['password'],
            request.json['fullName'],
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

    if website.settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
        send_confirm_email(user, email=user.username)
        message = language.REGISTRATION_SUCCESS.format(email=user.username)
        return {'message': message}
    else:
        return {'message': 'You may now log in.'}


# TODO: Remove me
def auth_register_post():
    if not website.settings.ALLOW_REGISTRATION:
        status.push_status_message(language.REGISTRATION_UNAVAILABLE)
        return redirect('/')
    form = RegistrationForm(request.form, prefix='register')
    set_previous_url()

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
            return auth_login(registration_form=form)
        if user:
            if website.settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
                send_confirm_email(user, email=user.username)
                message = language.REGISTRATION_SUCCESS.format(
                    email=user.username
                )
                status.push_status_message(message, 'success')
                return auth_login(registration_form=form)
            else:
                return redirect('/login/first/')
    else:
        forms.push_errors_to_status(form.errors)
        return auth_login(registration_form=form)


def resend_confirmation():
    """View for resending an email confirmation email.
    """
    form = ResendConfirmationForm(request.form)
    if request.method == 'POST':
        if form.validate():
            clean_email = form.email.data
            user = get_user(username=clean_email)
            if not user:
                return {'form': form}
            try:
                send_confirm_email(user, clean_email)
            except KeyError:  # already confirmed, redirect to dashboard
                status_message = 'Email has already been confirmed.'
                type_ = 'warning'
            else:
                status_message = 'Resent email to {0}'.format(clean_email)
                type_ = 'success'
            status.push_status_message(status_message, type_)
        else:
            forms.push_errors_to_status(form.errors)
    # Don't go anywhere
    return {'form': form}


def merge_user_get(**kwargs):
    '''Web view for merging an account. Renders the form for confirmation.
    '''
    return forms.utils.jsonify(MergeAccountForm())


# TODO: shrink me
@must_be_logged_in
def merge_user_post(auth, **kwargs):
    '''View for merging an account. Takes either JSON or form data.

    Request data should include a "merged_username" and "merged_password"
    properties for the account to be merged in.
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
            status.push_status_message("Could not authenticate. Please check "
                                       "your username and password.")
            return merge_user_get(**kwargs)
        merged_username = form.merged_username.data
        merged_password = form.merged_password.data
    try:
        merged_user = User.find_one(Q("username", "eq", merged_username))
    except NoResultsFound:
        status.push_status_message("Could not find that user. Please check the "
                                   "username and password.")
        return merge_user_get(**kwargs)
    if master and merged_user:
        if merged_user.check_password(merged_password):
            master.merge_user(merged_user)
            master.save()
            if request.form:
                status.push_status_message("Successfully merged {0} with this "
                                           "account".format(merged_username))
                return redirect("/settings/")
            return {"status": "success"}
        else:
            status.push_status_message("Could not find that user. Please check "
                                       "the username and password.")
            return merge_user_get(**kwargs)
    else:
        raise HTTPError(http.BAD_REQUEST)


# TODO: Is this used?
def auth_registerbeta():
    return redirect('/account')
