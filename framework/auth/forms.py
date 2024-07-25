from wtforms.widgets import CheckboxInput
from website import language
from wtforms import (
    Form,
    PasswordField,
    BooleanField,
    HiddenField,
    StringField,
    validators,
    ValidationError
)

from framework import auth
from framework.forms import (
    NoHtmlCharacters,
    BootstrapTextInput,
    BootstrapPasswordInput,
    stripped,
    lowerstripped,
)
##### Custom validators #####


class UniqueEmail:
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


class EmailExists:
    """Ensure that an email is in the database."""
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not auth.get_user(email=field.data):
            msg = self.message or language.EMAIL_NOT_FOUND.format(email=field.data)
            raise ValidationError(msg)

##### Custom fields #####


# The order fields are defined determines their order on the page.
name_field = StringField(
    'Full Name',
    [
        validators.DataRequired(message='Full name is required'),
        NoHtmlCharacters(),
    ],
    filters=[stripped],
    widget=BootstrapTextInput(),
)

name_field_not_required = StringField(
    'Full Name',
    [
        NoHtmlCharacters(),
    ],
    filters=[stripped],
    widget=BootstrapTextInput(),
)

email_field = StringField('Email Address',
    [
        validators.DataRequired(message='Email address is required'),
        validators.Length(min=6, message='Email address is too short'),
        validators.Length(max=120, message='Email address is too long'),
        validators.Email(message='Email address is invalid'),
        NoHtmlCharacters(),
    ],
    filters=[lowerstripped],
    widget=BootstrapTextInput())


unique_email_field = StringField('Email Address',
    [
        validators.DataRequired(message='Email address is required'),
        validators.Length(min=6, message='Email address is too short'),
        validators.Length(max=120, message='Email address is too long'),
        validators.Email(message='Email address is invalid'),
        NoHtmlCharacters(),
        UniqueEmail(),
    ],
    filters=[lowerstripped],
    widget=BootstrapTextInput())

confirm_email_field = StringField(
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
        validators.DataRequired(message='Password is required'),
        validators.Length(min=8, message='Password is too short. '
            'Password should be at least 8 characters.'),
        validators.Length(max=255, message='Password is too long. '
            'Password should be at most 255 characters.'),
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


class ResetPasswordForm(Form):
    password = PasswordField('New Password',
        [
            validators.DataRequired(message='Password is required'),
            validators.Length(min=8, message='Password is too short. '
                'Password should be at least 8 characters.'),
            validators.Length(max=255, message='Password is too long. '
                'Password should be at most 255 characters.'),
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


class SetEmailAndPasswordForm(ResetPasswordForm):
    token = HiddenField()
    accepted_terms_of_service = BooleanField(
        [
            validators.DataRequired(message='This field is required'),
        ]
    )


class SignInForm(Form):
    username = email_field
    password = password_field


class ResendConfirmationForm(Form):
    name = name_field_not_required  # If the user's auth already has a fullname this won't appear.
    email = email_field
    accepted_terms_of_service = BooleanField(
        [
            validators.DataRequired(message='This field is required'),
        ],
        widget=CheckboxInput()
    )


class PasswordForm(Form):
    password = password_field


class ForgotPasswordForm(Form):
    email = email_field
