# -*- coding: utf-8 -*-
import httplib as http
import logging
import datetime

from modularodm.exceptions import NoResultsFound, ValidationValueError
import framework
from framework import set_previous_url, request
from framework import status, exceptions
import framework.forms as forms
from framework import auth
from framework.auth import login, logout, DuplicateEmailError, get_user, get_current_user
from framework.auth.forms import (RegistrationForm, SignInForm,
    ForgotPasswordForm, ResetPasswordForm, MergeAccountForm, ResendConfirmationForm)

import website.settings
from website import security, mails, language


Q = framework.Q
User = framework.auth.model.User
logger = logging.getLogger(__name__)


def reset_password(*args, **kwargs):

    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(framework.request.form)

    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        error_data = {'message_short': 'Invalid url.',
            'message_long': 'The verification key in the URL is invalid or '
            'has expired.'}
        raise exceptions.HTTPError(400, data=error_data)

    if request.method == 'POST' and form.validate():
        user_obj.verification_key = None
        user_obj.set_password(form.password.data)
        user_obj.save()
        status.push_status_message('Password reset')
        return framework.redirect('/account/')

    forms.push_errors_to_status(form.errors)
    return {
        'verification_key': verification_key,
    }


def forgot_password():
    form = ForgotPasswordForm(framework.request.form, prefix='forgot_password')

    if form.validate():
        email = form.email.data
        user_obj = get_user(username=email)
        if user_obj:
            user_obj.verification_key = security.random_string(20)
            user_obj.save()
            reset_link = "http://{0}{1}".format(
                framework.request.host,
                framework.url_for(
                    'OsfWebRenderer__reset_password',
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
            status.push_status_message('Email {email} not found'.format(email=email))

    forms.push_errors_to_status(form.errors)
    return auth_login(forgot_password_form=form)


###############################################################################
# Log in
###############################################################################

def auth_login(registration_form=None, forgot_password_form=None, **kwargs):
    """If GET request, show login page. If POST, attempt to log user in if
    login form passsed; else send forgot password email.

    """
    if get_current_user():
        if not request.args.get('logout'):
            return framework.redirect('/dashboard/')
        logout()
    direct_call = registration_form or forgot_password_form
    if framework.request.method == 'POST' and not direct_call:
        form = SignInForm(framework.request.form)
        if form.validate():
            try:
                response = login(form.username.data, form.password.data)
                return response
            except auth.LoginNotAllowedError:
                status.push_status_message(language.UNCONFIRMED, 'warning')
                # Don't go anywhere
                return {'next': ''}
            except auth.PasswordIncorrectError:
                status.push_status_message(language.LOGIN_FAILED)
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

    if next_url:
        status.push_status_message(language.MUST_LOGIN)
    return {
        'next': next_url,
    }


def auth_logout():
    """Log out and delete cookie.

    """
    logout()
    rv = framework.redirect('/goodbye/')
    rv.delete_cookie(website.settings.COOKIE_NAME)
    return rv


def confirm_email_get(**kwargs):
    """View for email confirmation links.
    Authenticates and redirects to user settings page if confirmation is
    successful, otherwise shows an "Expired Link" error.

    methods: GET
    """
    user = get_user(id=kwargs['uid'])
    token = kwargs['token']
    if user:
        if user.confirm_email(token):  # Confirm and register the usre
            user.date_last_login = datetime.datetime.utcnow()
            user.save()
            # Go to settings page
            status.push_status_message(language.WELCOME_MESSAGE, 'success')
            response = framework.redirect('/settings/')
            return auth.authenticate(user, response=response)
    # Return data for the error template
    return {'code': 400, 'message_short': 'Link Expired', 'message_long': language.LINK_EXPIRED}, 400


def send_confirm_email(user, email):
    """Sends a confirmation email to `user` to a given email.

    :raises: KeyError if user does not have a confirmation token for the given
        email.
    """
    confirmation_url = user.get_confirmation_url(email, external=True)
    mails.send_mail(email, mails.CONFIRM_EMAIL, 'plain',
        user=user,
        confirmation_url=confirmation_url)


def auth_register_post():
    if not website.settings.ALLOW_REGISTRATION:
        status.push_status_message(language.REGISTRATION_UNAVAILABLE)
        return framework.redirect('/')
    form = RegistrationForm(framework.request.form, prefix='register')
    set_previous_url()

    # Process form
    if form.validate():
        try:
            user = auth.register_unconfirmed(
                form.username.data,
                form.password.data,
                form.fullname.data)
            auth.signals.user_registered.send(user)
        except (ValidationValueError, DuplicateEmailError):
            status.push_status_message(
                language.ALREADY_REGISTERED.format(email=form.username.data))
            return auth_login(registration_form=form)
        if user:
            if website.settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
                send_confirm_email(user, email=user.username)
                message = language.REGISTRATION_SUCCESS.format(email=user.username)
                status.push_status_message(message, 'success')
                return auth_login(registration_form=form)
            else:
                return framework.redirect('/login/first/')
                #status.push_status_message('You may now log in')
            return framework.redirect(framework.url_for('OsfWebRenderer__auth_login'))
    else:
        forms.push_errors_to_status(form.errors)
        return auth_login(registration_form=form)

def resend_confirmation():
    """View for resending an email confirmation email.
    """
    form = ResendConfirmationForm(framework.request.form)
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
                status_message = 'Resent email to <em>{0}</em>'.format(clean_email)
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
def merge_user_post(**kwargs):
    '''View for merging an account. Takes either JSON or form data.

    Request data should include a "merged_username" and "merged_password" properties
    for the account to be merged in.
    '''
    master = get_current_user()
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
                status.push_status_message("Successfully merged {0} with this account".format(merged_username))
                return framework.redirect("/settings/")
            return {"status": "success"}
        else:
            status.push_status_message("Could not find that user. Please check the username and password.")
            return merge_user_get(**kwargs)
    else:
        raise framework.exceptions.HTTPError(http.BAD_REQUEST)


def auth_registerbeta():
    return framework.redirect('/account')
