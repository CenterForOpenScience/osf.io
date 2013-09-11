from framework.forms import (
    Form,
    NoHtmlCharacters,
    PasswordField,
    TextField,
    validators,
)

email_field = TextField('Email Address', [
    validators.Required(message=u'Email address is required'),
    validators.Length(min=6, message=u'Email address is too short'),
    validators.Length(max=120, message=u'Email address is too long'),
    validators.Email(message=u'Email address is invalid'),
    NoHtmlCharacters(),
])

password_field = PasswordField('Password', [
    validators.Required(message=u'Password is required'),
    validators.Length(min=6, message=u'Password is too short'),
    validators.Length(max=35, message=u'Password is too long'),
])


class ResetPasswordForm(Form):
    password = password_field
    password2 = PasswordField(
        'Verify Password',
        [
            validators.EqualTo('password', message='Passwords must match'),
        ],
    )


class RegistrationForm(Form):
    fullname = TextField(
        'Full Name',
        [
            validators.Required(message=u'Full name is required'),
            NoHtmlCharacters(),
        ],
    )
    username = email_field
    username2 = TextField(
        'Verify Email Address',
        [
            validators.EqualTo(
                'username',
                message='Email addresses must match'),
        ],
    )
    password = password_field
    password2 = PasswordField(
        'Verify Password',
        [
            validators.EqualTo('password', message='Passwords must match')
        ],
    )


class SignInForm(Form):
    username = email_field
    password = password_field


class ForgotPasswordForm(Form):
    email = email_field