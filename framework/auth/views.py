import framework
from framework import goback, set_previous_url, push_status_message
from framework.email.tasks import send_email
import framework.status as status
import framework.forms as forms

import website.settings
import settings

import helper

from framework.auth import register, login, logout, DuplicateEmailError, get_user
from framework.auth.forms import RegistrationForm, SignInForm, ForgotPasswordForm, ResetPasswordForm


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
            send_email.delay(
                to=form.email.data,
                subject="Reset Password",
                message="http://%s%s" % (
                    framework.request.host,
                    framework.url_for(
                        'OsfWebRenderer__reset_password',
                        verification_key=user_obj.verification_key
                    )
                )
            )
            status.push_status_message('Reset email sent')
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
    if not website.settings.allow_registration:
        status.push_status_message('We are currently in beta development and \
            registration is only available to those with beta invitations. If you \
            would like to be added to the invitation list, please email \
            beta@openscienceframework.org.')
        return framework.redirect('/')

    form = RegistrationForm(framework.request.form, prefix='register')

    if not settings.registrationEnabled:
        status.push_status_message('Registration is currently disabled')
        return framework.redirect(framework.url_for('auth_login'))

    set_previous_url()

    # Process form
    if form.validate():
        try:
            u = register(form.username.data, form.password.data, form.fullname.data)
        except DuplicateEmailError:
            status.push_status_message('The email <em>%s</em> has already been registered.' % form.username.data)
            return auth_login(registration_form=form)
        if u:
            if website.settings.confirm_registrations_by_email:
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
                status.push_status_message('You may now login')
            return framework.redirect('/')

    else:
        forms.push_errors_to_status(form.errors)

        return auth_login(registration_form=form)


def auth_registerbeta():
    return framework.redirect('/account')
