import framework.status as status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators

from wtforms.widgets import TextInput, PasswordInput, html_params, TextArea, Select
from wtforms.validators import ValidationError

from wtfrecaptcha.fields import RecaptchaField

from website.util.sanitize import scrub_html


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


class JqueryAutocomplete(TextInput):
    def __call__(self, field, **kwargs):
        return ''.join((
            super(JqueryAutocomplete, self).__call__(field, **kwargs),
            self._script(field.name),
        ))

    def _script(self, field):
        return """
        <script>
            (function($) {
                $(function() {

                    var id = '%s';
                    var old_elem = $('#' + id);

                    var replace_with = function(el) {
                        old_elem.hide()
                        var old_field = old_elem.data('replacement');
                        if(typeof(old_field) !== 'undefined') {
                            old_field.remove()
                        }
                        old_elem.data('replacement', el)
                        old_elem.after(el)
                        el.data('replaces', old_elem)
                    }

                    var replace_with_input = function() {
                        input = $('<div class="input-group">' +
                                '<input class="form-control"/>' +
                                '<span class="input-group-btn">' +
                                    '<button class="btn btn-default" type="button">' +
                                        '<span class="caret"/>' +
                                    '</button>' +
                                '</span>' +
                            '</div>');

                        var cache = {};

                        input.find('input.form-control').catcomplete({
                                source: function(request, response) {
                                    if(request.term in cache) {
                                        response(cache[request.term]);
                                        return;
                                    }

                                    $.getJSON(
                                        '/api/v1/search/projects/',
                                        request,
                                        function(data, status, xhr) {
                                            cache[request.term] = data;
                                            response(cache[request.term]);
                                            return;
                                        }
                                    );
                                },
                                minLength: 0,
                                select: function(event, ui) {
                                    replace_with_selection(ui.item)
                                    return false;
                                },
                                open: function(event, ui) {
                                    $(event.target).data('autocomplete-open', true);
                                },
                                close: function(event, ui) {
                                    $(event.target).data('autocomplete-open', false);
                                }
                            })
                        replace_with(input);
                        old_elem.val('');

                        input.find('.btn-default').on('click', function(e) {
                            e.preventDefault();
                            var elem = input.find('input.form-control');
                            elem.catcomplete( elem.data('autocomplete-open') ? 'close' : 'search' );

                        })
                    }

                    var replace_with_selection = function(project) {
                        replace_with(
                            $('<div class="panel panel-default autocomplete-selection">' +
                                '<div class="panel-heading">' +
                                    '<h3 class="panel-title">' +
                                        '<span class="pull-right remove-autocomplete-selection">&times;</span>' +
                                        project.label +
                                    '</h3>' +
                                '</div>' +
                                '<div class="panel-body">' +
                                    project.authors +
                                '</div>' +
                            '</div>')
                        );
                        old_elem.val(project.id);
                    }

                    replace_with_input();

                    $('body').on('click', '.remove-autocomplete-selection', function(e) {
                        replace_with_input();
                    })
                });
            })(jQuery);
            </script>
        """ % field


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
        self.message = message or u'HTML is not allowed in form field'

    def __call__(self, form, field):
        if not field.data == scrub_html(field.data):
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
