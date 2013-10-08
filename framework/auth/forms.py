from framework.forms import (
    Form,
    NoHtmlCharacters,
    PasswordField,
    TextField,
    validators,
    BootstrapTextInput,
    BootstrapPasswordInput
)


# The order fields are defined determines their order on the page.
name_field = TextField(
    'Full Name',
    [
        validators.Required(message=u'Full name is required'),
        NoHtmlCharacters(),
    ],
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
    widget=BootstrapTextInput())

confirm_email_field = TextField(
    'Verify Email Address',
    [
        validators.EqualTo(
            'username',
            message='Email addresses must match'),
    ],
    widget=BootstrapTextInput(),
)

password_field = PasswordField('Password',
    [
        validators.Required(message=u'Password is required'),
        validators.Length(min=6, message=u'Password is too short'),
        validators.Length(max=35, message=u'Password is too long'),
    ],
    widget=BootstrapPasswordInput()
)

confirm_password_field = PasswordField(
    'Verify Password',
    [
        validators.EqualTo('password', message='Passwords must match')
    ],
    widget=BootstrapPasswordInput()
)


class ResetPasswordForm(Form):
    password = password_field
    password2 = confirm_password_field


class RegistrationForm(Form):
    fullname = name_field
    username = email_field
    username2 = confirm_email_field
    password = password_field
    password2 = confirm_password_field


class SignInForm(Form):
    username = email_field
    password = password_field


class ForgotPasswordForm(Form):
    email = email_field
