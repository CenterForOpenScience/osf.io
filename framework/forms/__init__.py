import framework.status as status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators
from wtforms.widgets import TextInput
from wtforms.validators import ValidationError

from wtfrecaptcha.fields import RecaptchaField

from framework.forms.utils import sanitize

# from wtforms.ext.sqlalchemy.orm import model_form


class MyTextInput(TextInput):
    def __init__(self, error_class=u'has_errors'):
        super(MyTextInput, self).__init__()

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'span12')
        return super(MyTextInput, self).__call__(field, **kwargs)

RecaptchaField = RecaptchaField

validators = validators


def push_errors_to_status(errors):
    if errors:
        for field, throwaway in errors.items():
            for error in errors[field]:
                status.push_status_message(error)


class NoHtmlCharacters(object):
    """ Raises a validation error if an email address contains characters that
    we escape for HTML output

    TODO: This could still post a problem if we output an email address to a
    Javascript literal.
    """

    def __init__(self, message=None):
        self.message = message or u'Illegal characters in field'

    def __call__(self, form, field):
        if not field.data == sanitize(field.data):
            raise ValidationError(self.message)