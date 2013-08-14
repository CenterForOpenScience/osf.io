import framework
import framework.Email as Email
import framework.Beaker as Session
import framework.Mako as Template
import framework.Status as Status
import framework.Forms as Forms

import Site.Settings
import Settings

import Helper

from framework.Auth import *
from framework.Auth.Forms import *

@framework.get('/resetpassword/<verification_key>')
@framework.post('/resetpassword/<verification_key>')
def reset_password(*args, **kwargs):
    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(framework.request.form)

    if form.validate():
        user_obj = getUser(verification_key=verification_key)
        if user_obj:
            user_obj.verification_key = None
            user_obj.password = hash_password(form.password.data)
            user_obj.save()
            Status.pushStatusMessage('Password reset')
            return framework.redirect('/account')

    return Template.render(
        filename='resetpassword.mako',
        form_resetpassword=form,
        verification_key = verification_key,
    )

@framework.post('/forgotpassword')
def forgot_password():
    form = ForgotPasswordForm(framework.request.form, prefix='forgot_password')

    if form.validate():
        user_obj = getUser(username=form.email.data)
        if user_obj:
            user_obj.verification_key = Helper.randomString(20)
            user_obj.save()
            Email.sendEmail(
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
            Status.pushStatusMessage('Reset email sent')
            return framework.redirect('/')
        else:
            Status.pushStatusMessage('Email {email} not found'.format(email=form.email.data))

    Forms.pushErrorsToStatus(form.errors)
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
                    Status.pushStatusMessage('''Please check your email (and spam
                        folder) and click the verification link before logging
                        in.''')
                    return Session.goback()
                return framework.redirect('/dashboard')
            else:
                Status.pushStatusMessage('''Log-in failed. Please try again or
                    reset your password''')
    
        Forms.pushErrorsToStatus(form.errors)
    
    return Template.render(
        filename=Settings.auth_tpl_register, form_registration=formr, 
        form_forgotpassword=formf, form_signin=form, prettify=True)

@framework.get('/logout')
def auth_logout():
    logout()
    Status.pushStatusMessage('You have successfully logged out.')
    return framework.redirect('/')

@framework.post("/register")
def auth_register_post():
    if not Site.Settings.allow_registration:
        Status.pushStatusMessage('We are currently in beta development and \
            registration is only available to those with beta invitations. If you \
            would like to be added to the invitation list, please email \
            beta@openscienceframework.org.')
        return framework.redirect('/')

    form = RegistrationForm(framework.request.form, prefix='register')

    if not Settings.registrationEnabled:
        Status.pushStatusMessage('Registration is currently disabled')
        return framework.redirect(framework.url_for('auth_login'))

    Session.setPreviousUrl()

    # Process form
    if form.validate():
        try:
            u = register(form.username.data, form.password.data, form.fullname.data)
        except DuplicateEmailError:
            Status.pushStatusMessage('The email <em>%s</em> has already been registered.' % form.username.data)
            return auth_login(registration_form=form)
        if u:
            if Site.Settings.confirm_registrations_by_email:
                # TODO: The sendRegistration method does not exist, this block
                #   will fail if email confirmation is on.
                raise NotImplementedError(
                    'Registration confirmation by email has not been fully'
                    'implemented.'
                )
                sendRegistration(u)
                Status.pushStatusMessage('Registration successful. Please \
                    check %s to confirm your email address, %s.' %
                    (str(u.username), str(u.fullname)))
            else:
                Status.pushStatusMessage('You may now login')
            return framework.redirect('/')

    else:
        Forms.pushErrorsToStatus(form.errors)

        return auth_login(registration_form=form)


@framework.get("/midas")
@framework.get("/summit")
@framework.get("/accountbeta")
@framework.get("/decline")
def auth_registerbeta():
    return framework.redirect('/account')
