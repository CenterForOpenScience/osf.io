# -*- coding: utf-8 -*-
import httplib as http
import logging

import framework
from framework import goback, set_previous_url, push_status_message, request
from framework.email.tasks import send_email
import framework.status as status
import framework.forms as forms


import website.settings  # TODO: Use framework settings module instead
import settings

import helper

import framework.auth
from framework.auth import  register, login, logout, DuplicateEmailError, get_user, must_have_session_auth
from framework.auth.forms import RegistrationForm, SignInForm, ForgotPasswordForm, ResetPasswordForm

Q = framework.Q
User = framework.auth.model.User
logger = logging.getLogger(__name__)

def reset_password(*args, **kwargs):

    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(framework.request.form)

    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        push_status_message('Invalid verification key')
        return {
            'verification_key': verification_key
        }

    if form.validate():
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
        user_obj = get_user(username=form.email.data)
        if user_obj:
            user_obj.verification_key = helper.random_string(20)
            user_obj.save()
            # TODO: This is OSF-specific
            success = send_email.delay(
                from_addr=website.settings.FROM_EMAIL,
                to_addr=form.email.data,
                subject="Reset Password",
                message="http://%s%s" % (
                    framework.request.host,
                    framework.url_for(
                        'OsfWebRenderer__reset_password',
                        verification_key=user_obj.verification_key
                    )
                )
            )
            if success:
                status.push_status_message('Reset email sent')
            else:
                status.push_status_message("Could not send email. Please try again later.")
            return framework.redirect('/')
        else:
            status.push_status_message('Email {email} not found'.format(email=form.email.data))

    forms.push_errors_to_status(form.errors)
    return auth_login(forgot_password_form=form)


###############################################################################
# Log in
###############################################################################

def auth_login(
        registration_form=None,
        forgot_password_form=None
):
    direct_call = True if registration_form or forgot_password_form else False

    if framework.request.method == 'POST' and not direct_call:
        form = SignInForm(framework.request.form)
        if form.validate():
            response = login(form.username.data, form.password.data)
            if response:
                if response == 2:
                    status.push_status_message('''Please check your email (and spam
                        folder) and click the verification link before logging
                        in.''')
                    return goback()
                return response
            else:
                status.push_status_message('''Log-in failed. Please try again or
                    reset your password''')

        forms.push_errors_to_status(form.errors)

    return {}

def auth_logout():
    logout()
    status.push_status_message('You have successfully logged out.')
    return framework.redirect('/')

def auth_register_post():
    if not website.settings.ALLOW_REGISTRATION:
        status.push_status_message('We are currently in beta development and \
            registration is only available to those with beta invitations. If you \
            would like to be added to the invitation list, please email \
            beta@openscienceframework.org.')
        return framework.redirect('/')

    form = RegistrationForm(framework.request.form, prefix='register')

    if not settings.registrationEnabled:
        status.push_status_message('Registration is currently disabled')
        return framework.redirect(framework.url_for('OsfWebRenderer__auth_login'))

    set_previous_url()

    # Process form
    if form.validate():
        try:
            u = register(form.username.data, form.password.data, form.fullname.data)
        except DuplicateEmailError:
            status.push_status_message('The email <em>%s</em> has already been registered.' % form.username.data)
            return auth_login(registration_form=form)
        if u:
            if website.settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
                # TODO: The sendRegistration method does not exist, this block
                #   will fail if email confirmation is on.
                raise NotImplementedError(
                    'Registration confirmation by email has not been fully'
                    'implemented.'
                )
                sendRegistration(u)
                status.push_status_message('Registration successful. Please \
                    check %s to confirm your email address, %s.' %
                    (str(u.username), str(u.fullname)))
            else:
                status.push_status_message('You may now log in')
            return framework.redirect(framework.url_for('OsfWebRenderer__auth_login'))

    else:
        forms.push_errors_to_status(form.errors)

        return auth_login(registration_form=form)


@must_have_session_auth
def merge_user_post(**kwargs):
    '''API view for merging an account.

    Request JSON data should include a "username" and "password" properties
    for the account to be merged in.
    '''
    master = kwargs['user']
    merged_username = request.json.get("username")
    merged_password = request.json.get("password")
    merged_user = User.find_one(Q("username", "eq", merged_username))
    if master and merged_user:
        if merged_user.check_password(merged_password):
            master.merge_user(merged_user)
            master.save()
    else:
        raise framework.exceptions.HTTPError(http.BAD_REQUEST)


def auth_registerbeta():
    return framework.redirect('/account')
