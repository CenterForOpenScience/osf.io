# -*- coding: utf-8 -*-

# TODO: Remove me

from wtforms import ValidationError

from framework import auth
from framework.forms import (
    Form,
    NoHtmlCharacters,
    PasswordField,
    TextField,
    HiddenField,
    validators,
    BootstrapTextInput,
    BootstrapPasswordInput,
    stripped,
    lowerstripped
)
from website import language


##### Custom validators #####

class UniqueEmail(object):
    """Ensure that an email is not already in the database."""
    def __init__(self, message=None, allow_unregistered=True):
        self.message = message
        self.allow_unregistered = allow_unregistered

    def __call__(self, form, field):
        user = auth.get_user(email=field.data)
        if user:
            if self.allow_unregistered and not user.is_registered:
                return True
            msg = self.message or language.ALREADY_REGISTERED.format(email=field.data)
            raise ValidationError(msg)
        return True


class EmailExists(object):
    """Ensure that an email is in the database."""
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not auth.get_user(email=field.data):
            msg = self.message or language.EMAIL_NOT_FOUND.format(email=field.data)
            raise ValidationError(msg)

##### Custom fields #####


# The order fields are defined determines their order on the page.
name_field = TextField(
    'Full Name',
    [
        validators.Required(message=u'Full name is required'),
        NoHtmlCharacters(),
    ],
    filters=[stripped],
    widget=BootstrapTextInput(),
)

email_field = TextField('Email Address',
    [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'),
        validators.Length(max=120, message=u'Email address is too long'),
        validators.Email(message=u'Email address is invalid'),
        NoHtmlCharacters(),
    ],
    filters=[lowerstripped],
    widget=BootstrapTextInput())


unique_email_field = TextField('Email Address',
    [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'),
        validators.Length(max=120, message=u'Email address is too long'),
        validators.Email(message=u'Email address is invalid'),
        NoHtmlCharacters(),
        UniqueEmail(),
    ],
    filters=[lowerstripped],
    widget=BootstrapTextInput())

confirm_email_field = TextField(
    'Verify Email Address',
    [
        validators.EqualTo(
            'username',
            message='Email addresses must match'),
    ],
    filters=[lowerstripped],
    widget=BootstrapTextInput(),
)

password_field = PasswordField('Password',
    [
        validators.Required(message=u'Password is required'),
        validators.Length(min=6, message=u'Password is too short. '
            'Password should be at least 6 characters.'),
        validators.Length(max=256, message=u'Password is too long. '
            'Password should be at most 256 characters.'),
    ],
    filters=[stripped],
    widget=BootstrapPasswordInput()
)

confirm_password_field = PasswordField(
    'Verify Password',
    [
        validators.EqualTo('password', message='Passwords must match')
    ],
    filters=[stripped],
    widget=BootstrapPasswordInput()
)


class SetEmailAndPasswordForm(Form):
    password = PasswordField('New Password',
        [
            validators.Required(message=u'Password is required'),
            validators.Length(min=6, message=u'Password is too short. '
                'Password should be at least 6 characters.'),
            validators.Length(max=256, message=u'Password is too long. '
                'Password should be at most 256 characters.'),
        ],
        filters=[stripped],
        widget=BootstrapPasswordInput()
    )

    password2 = PasswordField(
        'Verify New Password',
        [
            validators.EqualTo('password', message='Passwords must match')
        ],
        filters=[stripped],
        widget=BootstrapPasswordInput()
    )

    token = HiddenField()


# TODO: use unique email field and remove redundant status message and
# validation in the views
class RegistrationForm(Form):
    fullname = name_field
    username = email_field
    username2 = confirm_email_field
    password = password_field
    password2 = confirm_password_field


class SignInForm(Form):
    username = email_field
    password = password_field


class ResendConfirmationForm(Form):
    email = email_field


class PasswordForm(Form):
    password = password_field


class ForgotPasswordForm(Form):
    email = email_field


class MergeAccountForm(Form):
    merged_username = TextField("Duplicate User's Email Address",
    [
        validators.Required(message=u'Email address is required'),
        validators.Length(min=6, message=u'Email address is too short'),
        validators.Length(max=120, message=u'Email address is too long'),
        validators.Email(message=u'Email address is invalid'),
        NoHtmlCharacters(),
        EmailExists(),
    ],
        filters=[lowerstripped],
        widget=BootstrapTextInput())
    merged_password = PasswordField("Duplicate User's Password",
                                    [validators.Required(
                                        message=u"Please enter the user's password")],
                                    filters=[stripped],
                                    widget=BootstrapPasswordInput())
    user_password = PasswordField("This Account's Password",
                                    [validators.Required(
                                        message=u"Please enter the password for this account")],
                                    filters=[stripped],
                                    widget=BootstrapPasswordInput())
