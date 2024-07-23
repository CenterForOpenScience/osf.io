from wtforms import Form, BooleanField, StringField, validators

###############################################################################
# Forms
###############################################################################


class NewNodeForm(Form):
    title = StringField('Title', [
        validators.DataRequired(message='Title is required'),
        validators.Length(min=1, message='Title must contain at least 1 character.'),
        validators.Length(max=200, message='Title must contain fewer than 200 characters.')
    ])
    description = StringField('Description')
    category = StringField('Category')
    inherit_contributors = BooleanField('Inherit')
