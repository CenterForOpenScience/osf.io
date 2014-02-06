# -*- coding: utf-8 -*-
import httplib as http
import logging

import framework
from framework import goback, set_previous_url, request, redirect, session
from framework.email.tasks import send_email
from framework import status
import framework.forms as forms
from modularodm.exceptions import NoResultsFound


import website.settings  # TODO: Use framework settings module instead
import settings

import helper

import framework.auth
from framework.auth import register, login, logout, DuplicateEmailError, get_user, get_current_user
from framework.auth.forms import RegistrationForm, SignInForm, ForgotPasswordForm, ResetPasswordForm, MergeAccountForm

Q = framework.Q
User = framework.auth.model.User
logger = logging.getLogger(__name__)

def reset_password(*args, **kwargs):

    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(framework.request.form)

    user_obj = get_user(verification_key=verification_key)
    if not user_obj:
        status.push_status_message('Invalid verification key')
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
            success = send_email(
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

def auth_login(registration_form=None, forgot_password_form=None, **kwargs):
    """If GET request, show login page. If POST, attempt to log user in if
    login form passsed; else send forgot password email.

    """
    direct_call = registration_form or forgot_password_form

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
    if next_url:
        status.push_status_message('You must log in to access this resource')
    return {
        'next': next_url,
    }

def auth_logout():
    """Log out and delete cookie.

    """
    logout()
    status.push_status_message('You have successfully logged out.')
    rv = framework.redirect('/goodbye/')
    rv.delete_cookie(website.settings.COOKIE_NAME)
    return rv

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
                return framework.redirect('/login/first/')
                #status.push_status_message('You may now log in')
            return framework.redirect(framework.url_for('OsfWebRenderer__auth_login'))

    else:
        forms.push_errors_to_status(form.errors)

        return auth_login(registration_form=form)


def merge_user_get(**kwargs):
    '''Web view for merging an account. Renders the form for confirmation.
    '''
    return forms.utils.jsonify(MergeAccountForm())


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
        logger.debug("Failed to find user to merge")
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
