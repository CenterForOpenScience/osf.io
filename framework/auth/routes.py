import framework
import framework.email as email
import framework.beaker as Session
import framework.mako as template
import framework.status as status
import framework.forms as forms

import website.settings
import settings

import helper

from framework.auth import register, login, logout, DuplicateEmailError
from framework.auth.forms import RegistrationForm, SignInForm, ForgotPasswordForm, ResetPasswordForm

@framework.get('/resetpassword/<verification_key>')
@framework.post('/resetpassword/<verification_key>')
def reset_password(*args, **kwargs):
    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(framework.request.form)

    if form.validate():
        user_obj = get_user(verification_key=verification_key)
        if user_obj:
            user_obj.verification_key = None
            user_obj.password = hash_password(form.password.data)
            user_obj.save()
            status.push_status_message('Password reset')
            return framework.redirect('/account')

    return template.render(
        filename='resetpassword.mako',
        form_resetpassword=form,
        verification_key = verification_key,
    )

@framework.post('/forgotpassword')
def forgot_password():
    form = ForgotPasswordForm(framework.request.form, prefix='forgot_password')

    if form.validate():
        user_obj = get_user(username=form.email.data)
        if user_obj:
            user_obj.verification_key = helper.random_string(20)
            user_obj.save()
            email.send_email(
                to=form.email.data, 
                subject="Reset Password", 
                message="http://%s%s" % (
                    framework.request.host,
                    framework.url_for(
                        'reset_password',
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
@framework.get("/login") #todo fix
@framework.get("/account")
@framework.post("/login")
def auth_login(
        registration_form=None,
        forgot_password_form=None
):
    form = SignInForm(framework.request.form)
    formr = registration_form or RegistrationForm(prefix='register')
    formf = forgot_password_form or ForgotPasswordForm(prefix='forgot_password')

    direct_call = True if registration_form or forgot_password_form else False

    if framework.request.method == 'POST' and not direct_call:
        if form.validate():
            user = login(form.username.data, form.password.data)
            if user:
                if user == 2:
                    status.push_status_message('''Please check your email (and spam
                        folder) and click the verification link before logging
                        in.''')
                    return Session.goback()
                return framework.redirect('/dashboard')
            else:
                status.push_status_message('''Log-in failed. Please try again or
                    reset your password''')
    
        forms.push_errors_to_status(form.errors)
    
    return template.render(
        filename=settings.auth_tpl_register, form_registration=formr,
        form_forgotpassword=formf, form_signin=form, prettify=True)

@framework.get('/logout')
def auth_logout():
    logout()
    status.push_status_message('You have successfully logged out.')
    return framework.redirect('/')

@framework.post("/register")
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

    Session.set_previous_url()

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


@framework.get("/midas")
@framework.get("/summit")
@framework.get("/accountbeta")
@framework.get("/decline")
def auth_registerbeta():
    return framework.redirect('/account')
