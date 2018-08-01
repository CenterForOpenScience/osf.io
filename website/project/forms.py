# -*- coding: utf-8 -*-
from framework.forms import Form, TextField, BooleanField, validators

###############################################################################
# Forms
###############################################################################


class NewNodeForm(Form):
    title = TextField('Title', [
        validators.Required(message='Title is required'),
        validators.Length(min=1, message='Title must contain at least 1 character.'),
        validators.Length(max=200, message='Title must contain fewer than 200 characters.')
    ])
    description = TextField('Description')
    category = TextField('Category')
    inherit_contributors = BooleanField('Inherit')
