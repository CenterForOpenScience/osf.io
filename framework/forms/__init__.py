import framework.status as status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators

from wtforms.widgets import TextInput, PasswordInput, html_params, TextArea, Select
from wtforms.validators import ValidationError

from wtfrecaptcha.fields import RecaptchaField

from framework.forms.utils import sanitize


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


class JqueryAutocomplete2(TextInput):
    def __call__(self, field, **kwargs):
        return ''.join((
            super(JqueryAutocomplete2, self).__call__(field, **kwargs),
            self._script,
        ))

    @property
    def _script(self):
        return '<!-- Script goes here -->'

class JqueryAutocomplete(BootstrapTextInput):

    def __call__(self, field, **kwargs):
        _id = field.id
        field.id = '_' + field.id
        field.name = field.id
        return ''.join((
            '<!-- Stuff goes here -->',
            super(JqueryAutocomplete, self).__call__(field, **kwargs),
            '''<input type="hidden" name="''', _id, '''" id="''', _id, '''"/>
            <script>$(function() {

                var hidden = $("#''', _id, '''");
                $("#''', field.id, '''").autocomplete({
                    source: '/api/v1/search/projects/',
                    minLength: 2,
                    select: function(event, ui) {
                        hidden.val( ui.item.id );
                        $(this).val( ui.item.label );
                        return false;
                    }
                }).on('change', function() {
                    hidden.val('');
                    $(this).val('');
                });
            });</script>''',
        ))


RecaptchaField = RecaptchaField

validators = validators


def push_errors_to_status(errors):
    if errors:
        for field, _ in errors.items():
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
