from Framework.Forms import *

class ResetPasswordForm(Form):
    password    = PasswordField('Password', [
        validators.Required(message=u'Password is required'),
        validators.Length(min=6, message=u'Password is too short'),
        validators.Length(max=35, message=u'Password is too long'),
        validators.EqualTo('password2', message='Passwords must match')
    ])
    password2    = PasswordField('Verify Password')

class RegistrationForm(Form):
    fullname = TextField('Full Name', [
        validators.Required(message=u'Full name is required')
    ])
    username    = TextField('Email Address', [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'), 
        validators.Length(max=120, message=u'Email address is too long'), 
        validators.Email(message=u'Email address is invalid'),
        validators.EqualTo('username2', message='Email addresses must match')
    ])
    username2   = TextField('Verify Email Address')
    password    = PasswordField('Password', [
        validators.Required(message=u'Password is required'),
        validators.Length(min=6, message=u'Password is too short'),
        validators.Length(max=35, message=u'Password is too long'),
        validators.EqualTo('password2', message='Passwords must match')
    ])
    password2    = PasswordField('Verify Password')

class SignInForm(Form):
    username    = TextField('Email Address', [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'), 
        validators.Length(max=120, message=u'Email address is too long'), 
        validators.Email(message=u'Email address is invalid')
    ])
    password    = PasswordField('Password', [
        validators.Required(message=u'Password is required'),
        validators.Length(min=6, message=u'Password is too short'),
        validators.Length(max=35, message=u'Password is too long'),
    ])

class ForgotPasswordForm(Form):
    email    = TextField('Email Address', [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'), 
        validators.Length(max=120, message=u'Email address is too long'), 
        validators.Email(message=u'Email address is invalid')
    ])