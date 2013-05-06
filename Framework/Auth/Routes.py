import Framework
import Framework.Email as Email
import Framework.Beaker as Session
import Framework.Mako as Template
import Framework.Status as Status
import Framework.Forms as Forms

import Site.Settings
import Settings

import Helper

from Framework.Auth import *
from Framework.Auth.Forms import *

@Framework.get('/resetpassword/<verification_key>')
@Framework.post('/resetpassword/<verification_key>')
def reset_password(*args, **kwargs):
    verification_key = kwargs['verification_key']
    form = ResetPasswordForm(Framework.request.form)

    if form.validate():
        user_obj = getUser(verification_key=verification_key)
        if user_obj:
            user_obj.verification_key = None
            user_obj.password = hash_password(form.password.data)
            user_obj.save()
            Status.pushStatusMessage('Password reset')
            return Framework.redirect('/account')

    return Template.render(
        filename='resetpassword.mako',
        form_resetpassword=form,
        verification_key = verification_key,
    )

@Framework.post('/forgotpassword')
def forgot_password():
    forms = SignInForm()
    formr = RegistrationForm()
    form = ForgotPasswordForm(Framework.request.form)

    if form.validate():
        user_obj = getUser(username=form.email.data)
        if user_obj:
            user_obj.verification_key = Helper.randomString(20)
            user_obj.save()
            Email.sendEmail(
                to=form.email.data, 
                subject="Reset Password", 
                message="http://{domain}/resetpassword/{key}".format(
                    domain=Site.Settings.domain,
                    key=user_obj.verification_key,
                )
            )
            Status.pushStatusMessage('Reset email sent')
            return Framework.redirect('/')
        else:
            Status.pushStatusMessage('Email {email} not found'.format(email=form.email.data))

    Forms.pushErrorsToStatus(form.errors)
    return Template.render(
        filename=Settings.auth_tpl_register, form_registration=formr, 
        form_forgotpassword=form, form_signin=forms, prettify=True)

###############################################################################
# Log in
###############################################################################
@Framework.get("/login") #todo fix
@Framework.post("/login")
def auth_login():
    form = SignInForm(Framework.request.form)
    formr = RegistrationForm()
    formf = ForgotPasswordForm()

    if form.validate():
        user = login(form.username.data, form.password.data)
        if user:
            if user == 2:
                Status.pushStatusMessage('''Please check your email (and spam 
                    folder) and click the verification link before logging 
                    in.''')
                return Session.goback()
            return Framework.redirect('/dashboard')
        else:
            Status.pushStatusMessage('''Log-in failed. Please try again or 
                reset your password''')
    
    Forms.pushErrorsToStatus(form.errors)
    
    return Template.render(
        filename=Settings.auth_tpl_register, form_registration=formr, 
        form_forgotpassword=formf, form_signin=form, prettify=True)

@Framework.get('/logout')
def auth_logout():
    logout()
    Status.pushStatusMessage('You have successfully logged out.')
    return Framework.redirect('/')

###############################################################################
# Register
###############################################################################

@Framework.get("/account")
def auth_register():
    formr = RegistrationForm()
    formsi = SignInForm()
    formf = ForgotPasswordForm()
    return Template.render(
        filename=Settings.auth_tpl_register, form_registration=formr, 
        form_forgotpassword=formf, form_signin=formsi, prettify=True)

@Framework.post("/register")
def auth_register_post():
    if Site.Settings.registrationDisabled:
        Status.pushStatusMessage('We are currently in beta development and \
            registration is only available to those with beta invitations. If you \
            would like to be added to the invitation list, please email \
            beta@openscienceframework.org.')
        return Framework.redirect('/')
    form = RegistrationForm(Framework.request.form)
    formsi = SignInForm()
    formf = ForgotPasswordForm()
    if Settings.registrationEnabled:
        Session.setPreviousUrl()
        error = False
    
        if form.validate():
            u = register(form.username.data, form.password.data, form.fullname.data)
            if u:
                if Site.Settings.emailOnRegister:
                    sendRegistration(u)
                    Status.pushStatusMessage('Registration successful. Please \
                        check %s to confirm your email address, %s.' % 
                        (str(u.username), str(u.fullname))) 
                else:
                    Status.pushStatusMessage('You may now login')
                return Framework.redirect('/')

        Forms.pushErrorsToStatus(form.errors)
    else:
        Status.pushStatusMessage('Registration is currently disabled')
    return Template.render(
        filename=Settings.auth_tpl_register, form_registration=form, 
        form_forgotpassword=formf, form_signin=formsi, prettify=True)

@Framework.get("/midas")
@Framework.get("/summit")
@Framework.get("/accountbeta")
@Framework.get("/decline")
def auth_registerbeta():
    return Framework.redirect('/account')
