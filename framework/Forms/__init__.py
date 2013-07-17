import framework.Status as Status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators
from wtforms.widgets import TextInput

from wtfrecaptcha.fields import RecaptchaField

# from wtforms.ext.sqlalchemy.orm import model_form

class MyTextInput(TextInput):
    def __init__(self, error_class=u'has_errors'):
        super(MyTextInput, self).__init__()

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'span12')
        return super(MyTextInput, self).__call__(field, **kwargs)

RecaptchaField = RecaptchaField

validators = validators

def pushErrorsToStatus(errors):
    if errors:
        for field, throwaway in errors.items():
            for error in errors[field]:
                Status.pushStatusMessage(error)