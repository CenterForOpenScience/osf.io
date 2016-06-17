import framework.status as status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators
from wtforms.widgets import TextInput, PasswordInput, html_params, TextArea, Select
from wtforms.validators import ValidationError

from website.util.sanitize import strip_html


validators = validators


class BootstrapTextInput(TextInput):
    '''Custom TextInput that sets a field's class to 'form-control'.'''
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        return super(BootstrapTextInput, self).__call__(field, **kwargs)


class BootstrapPasswordInput(PasswordInput):
    '''Custom PasswordInput that sets a field's class to 'form-control'.'''

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super(BootstrapPasswordInput, self).__call__(field, **kwargs)
        return html

class BootstrapTextArea(TextArea):
    '''Custom TextArea that sets a field's class to 'form-control'.'''

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super(BootstrapTextArea, self).__call__(field, **kwargs)
        return html


def push_errors_to_status(errors):
    # TODO: Review whether errors contain custom HTML. If so this change might cause some display anomalies.
    if errors:
        for field, _ in errors.items():
            for error in errors[field]:
                status.push_status_message(error, trust=False)


class NoHtmlCharacters(object):
    """ Raises a validation error if an email address contains characters that
    we escape for HTML output

    TODO: This could still post a problem if we output an email address to a
    Javascript literal.
    """
    # TODO: Improve this for a post-bleach world
    def __init__(self, message=None):
        self.message = message or u'HTML is not allowed in form field'

    def __call__(self, form, field):
        if not field.data == strip_html(field.data):
            raise ValidationError(self.message)

# Filters

def lowered(s):
    if s:
        return s.lower()
    return s

def lowerstripped(s):
    if s:
        return s.lower().strip()
    return s

def stripped(s):
    if s:
        return s.strip()
    return s
