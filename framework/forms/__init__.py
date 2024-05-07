import framework.status as status

from wtforms.widgets import TextInput, PasswordInput, TextArea
from wtforms.validators import ValidationError
from osf.utils.sanitize import strip_html


class BootstrapTextInput(TextInput):
    '''Custom TextInput that sets a field's class to 'form-control'.'''

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        return super().__call__(field, **kwargs)


class BootstrapPasswordInput(PasswordInput):
    '''Custom PasswordInput that sets a field's class to 'form-control'.'''

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super().__call__(field, **kwargs)
        return html


class BootstrapTextArea(TextArea):
    '''
    Custom TextArea that sets a field's class to 'form-control'.'''

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super().__call__(field, **kwargs)
        return html


def push_errors_to_status(errors):
    # TODO: Review whether errors contain custom HTML. If so this change might cause some display anomalies.
    if errors:
        for field, _ in errors.items():
            for error in errors[field]:
                status.push_status_message(error, trust=False)


class NoHtmlCharacters:
    """ Raises a validation error if an email address contains characters that
    we escape for HTML output

    TODO: This could still post a problem if we output an email address to a
    Javascript literal.
    """

    # TODO: Improve this for a post-bleach world
    def __init__(self, message=None):
        self.message = message or 'HTML is not allowed in form field'

    def __call__(self, form, field):
        field_data = field.data or ''  # we do not aim to check equality, we aim to verify absence of HTML
        if field_data != strip_html(field.data):
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
